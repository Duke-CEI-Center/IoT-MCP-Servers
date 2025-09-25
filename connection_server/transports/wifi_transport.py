import asyncio
import json
import logging
import contextlib
import time
import shutil, tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from .transport import Transport


class WifiTransport(Transport):
    """
    WifiTransport supports multiple TCP client connections, each with independent I/O,
    data logging, and per-connection queues, identified by client IP only.
    """
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 9000,
        heartbeat_interval: int = 10,
        data_dir: Optional[str] = None,
        data_file_prefix: Optional[str] = None,
        log_file: str = 'logs/wifi.log',
        **kwargs
    ):
        self.host = host
        self.port = port
        self.last_heartbeat: Dict[str, float] = {}
        self.heartbeat_interval = heartbeat_interval

        # Data directory and prefix
        base_data_dir = Path(data_dir) if data_dir else Path('data')
        self.base_data_dir = base_data_dir
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
        self.data_prefix = data_file_prefix or 'wifi'

        # General log file setup
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger('WifiTransport')
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)
        self.logger.info("WifiTransport initialized")

        # Server and connections state
        self._server: Optional[asyncio.base_events.Server] = None
        self._serve_task: Optional[asyncio.Task] = None
        # key: ip_key -> conn info
        self._conns: Dict[str, Dict] = {}

    async def open(self) -> None:
        """
        Start the TCP server to accept client connections.
        """
        self._server = await asyncio.start_server(
            self.handle_conn,
            self.host,
            self.port
        )
        self._serve_task = asyncio.create_task(self._server.serve_forever())
        self.logger.info(f"WifiTransport listening on {self.host}:{self.port}")

    async def send(self, msg: bytes, address: str) -> None:
        """
        Send a message to the client identified by its IP (safe format).
        """
        conn = self._conns.get(address)
        if conn:
            if not msg.endswith(b"\n"):
                msg = msg.rstrip(b"\r\n") + b"\n"
            await conn['queue'].put(msg)
            conn['logger'].debug(f"Queued msg for {address}: {msg!r}")
        else:
            self.logger.warning(f"No connection for {address}, dropping msg")

    async def close(self) -> None:
        """
        Gracefully shut down all client connections and the server.
        """
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if self._serve_task:
            self._serve_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._serve_task

        for ip_key, info in list(self._conns.items()):
            for t in info['tasks']:
                t.cancel()
            writer: asyncio.StreamWriter = info['writer']
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            info['logger'].info(f"Closed connection {ip_key}")
        self._conns.clear()
        self.logger.info("WifiTransport closed")

    async def handle_conn(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Accept a new client, set up its queue, data file, and I/O loops.
        Identified by IP only, so new connections from same IP reuse.
        """
        peer = writer.get_extra_info('peername') or ('unknown', 0)
        ip_key = peer[0].replace('.', '_')

        # Prepare per-connection queue and data file
        queue: asyncio.Queue = asyncio.Queue()
        data_file = self.base_data_dir / f"{self.data_prefix}_{ip_key}.jsonl"
        data_file.parent.mkdir(parents=True, exist_ok=True)

        # If existing connection, replace
        if ip_key in self._conns:
            old = self._conns[ip_key]
            for t in old['tasks']:
                t.cancel()
            with contextlib.suppress(Exception):
                old['writer'].close()
            self.logger.info(f"Replaced existing connection for IP {peer[0]}")

        # Prepare debug logger per connection
        debug_filename = f"{self.data_prefix}_{ip_key}.debug.log"
        debug_path = "logs" / Path(debug_filename)
        debug_path.parent.mkdir(parents=True, exist_ok=True)

        tcp_logger = logging.getLogger(f"tcp.{ip_key}")
        tcp_logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(debug_path, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)-5s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        tcp_logger.addHandler(fh)
        tcp_logger.propagate = False

        # Store connection info
        self._conns[ip_key] = {
            'reader': reader,
            'writer': writer,
            'queue': queue,
            'data_file': data_file,
            'logger': tcp_logger,
            'tasks': []
        }
        self.logger.info(f"Client connected: {peer}, id={ip_key}")

        # Start reader and writer tasks
        reader_task = asyncio.create_task(
            self._reader_loop(reader, data_file, ip_key)
        )
        writer_task = asyncio.create_task(
            self._writer_loop(writer, queue, ip_key)
        )
        self._conns[ip_key]['tasks'].extend([reader_task, writer_task])
        asyncio.create_task(self.heartbeat_monitor(reader, writer))


    async def heartbeat_monitor(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await asyncio.sleep(5.0)
        peer = writer.get_extra_info('peername') or ('unknown', 0)
        ip_key = peer[0].replace('.', '_')
        while True:
            elapse = time.time() - self.last_heartbeat[ip_key]
            if elapse < self.heartbeat_interval:
                await asyncio.sleep(1.0)
                continue
            tcp_logger = self._conns[ip_key]['logger']
            tcp_logger.warning(
                f"{ip_key} heartbeat timeout ({elapse:.1f}s), killing connection."
            )
            for t in self._conns[ip_key]['tasks']:
                t.cancel()
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

            data_dir = Path.cwd() / "data"
            file_path = data_dir / "mcu_available.jsonl"
            tmp = tempfile.NamedTemporaryFile('w', delete=False, dir=file_path.parent)
            with open(file_path, 'r') as fin, tmp:
                for line in fin:
                    obj = json.loads(line)  # 或者捕获 JSONError
                    if obj.get("connection", {}).get("address") != ip_key:
                        tmp.write(line)
            shutil.move(tmp.name, file_path)

            tcp_logger.info(f"MCU at {ip_key} disconnected.")
            for h in list(tcp_logger.handlers):
                tcp_logger.removeHandler(h)
                h.close()
            del self._conns[ip_key]
            self.last_heartbeat.pop(ip_key, None)
            break

    async def _reader_loop(
        self,
        reader: asyncio.StreamReader,
        data_file: Path,
        addr: str
    ) -> None:
        data_dir = Path.cwd() / "data"
        all_data = data_dir / "all.jsonl"
        conn = self._conns[addr]
        tcp_logger = conn['logger']

        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=0.1)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
                continue
            if not line:
                break

            if line == b"PING\n":
                self.last_heartbeat[addr] = time.time()
                tcp_logger.info("Received PING (heartbeat)")
                continue

            text = line.decode('utf-8', errors='ignore').rstrip()

            if "available_sensors" in text:
                payload = json.loads(text)
                entry = {
                    "connection": {"type": "wifi", "address": addr},
                    **payload
                }
                with open(data_dir / "mcu_available.jsonl", 'a') as fd:
                    fd.write(json.dumps(entry, ensure_ascii=False) + '\n')
                tcp_logger.info(f"Logged available_sensors: {payload}")
                continue

            try:
                payload = json.loads(text)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                entry = {"write_time": now, **payload}
                tcp_logger.info(f"Writing {entry}")
                with (
                    open(data_file, "a", encoding="utf-8") as df,
                    open(all_data, "a", encoding="utf-8") as ad
                ):
                    df.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    ad.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    df.flush(); ad.flush()
            except json.JSONDecodeError:
                tcp_logger.warning(f"Invalid JSON: {text!r}")

        tcp_logger.info(f"Reader loop terminated for {addr}")

    async def _writer_loop(
        self,
        writer: asyncio.StreamWriter,
        queue: asyncio.Queue,
        addr: str
    ) -> None:
        conn = self._conns[addr]
        tcp_logger = conn['logger']
        while True:
            msg = await queue.get()
            batch = [msg.rstrip()]
            while True:
                try:
                    more = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                batch.append(more.rstrip())
            payload = b"\n".join(batch) + b"\n"
            try:
                tcp_logger.info(f"Sending: {payload!r}")
                writer.write(payload)
                await writer.drain()
            except Exception as e:
                tcp_logger.error(f"Write error: {e}")
                break

        tcp_logger.info(f"Writer loop terminated for {addr}")
        # Cleanup logger handler
        handlers = tcp_logger.handlers[:]
        for h in handlers:
            tcp_logger.removeHandler(h)
            h.close()
