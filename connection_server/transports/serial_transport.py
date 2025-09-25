import asyncio
import json
import time
import logging
import contextlib
import shutil, tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import serial_asyncio
import serial.tools.list_ports

from .transport import Transport

class SerialTransport(Transport):
    """
    SerialTransport implements the Transport interface for serial connections.
    It manages multiple serial ports, handling I/O, heartbeats, and data logging.
    """
    def __init__(
        self,
        port_names: Optional[List[str]] = None,
        baudrate: int = 115200,
        heartbeat_interval: int = 10,
        data_file_prefix: str = "logs/serial"
    ):
        self.port_names = port_names
        self.baudrate = baudrate
        self.heartbeat_interval = heartbeat_interval
        self.data_file_prefix = data_file_prefix

        # Internal state
        self.queues: Dict[str, asyncio.Queue] = {}
        self.events_ready: Dict[str, asyncio.Event] = {}
        self.last_heartbeat: Dict[str, float] = {}
        self._tasks: List[asyncio.Task] = []

        # Logger for this transport
        self.logger = logging.getLogger("SerialTransport")
        self.logger.setLevel(logging.DEBUG)

    async def open(self):
        """
        Initialize and start handling all configured serial ports.
        """
        # Discover ports if not specified
        if not self.port_names:
            ports = serial.tools.list_ports.comports()
            if not ports:
                raise RuntimeError("No serial ports found")
            self.port_names = [p.device for p in ports]

        # Initialize queues and events
        for port in self.port_names:
            self.queues[port] = asyncio.Queue()
            self.events_ready[port] = asyncio.Event()

        # Launch a handler task per port
        for port in self.port_names:
            task = asyncio.create_task(self.handle_conn(port))
            self._tasks.append(task)

        self.logger.info(f"SerialTransport started for ports: {self.port_names}")

    async def send(self, msg: bytes, address: str):
        """
        Send a message to the specified serial port address.
        """
        event = self.events_ready.get(address)
        if event and event.is_set():
            await self.queues[address].put(msg)
            self.logger.debug(f"Queued msg to {address}: {msg!r}")
        else:
            self.logger.warning(f"Port {address} not ready, dropping msg")

    async def close(self):
        """
        Gracefully close all port handlers.
        """
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self.logger.info("SerialTransport closed")

    async def write(
        self,
        writer: asyncio.StreamWriter,
        queue: asyncio.Queue,
        logger: logging.Logger
    ):
        """
        Continuously write queued messages to the serial port.
        """
        while True:
            msg = await queue.get()
            if not msg.endswith(b"\n"):
                msg = msg.rstrip(b"\r\n") + b"\n"
            if msg == "Finish!":
                logger.info("Writer loop exiting gracefully")
                break
            logger.debug(f"Sending: {msg!r}")
            writer.write(msg)
            await writer.drain()

    async def handle_conn(
        self,
        port: str
    ):
        """
        Manage I/O, heartbeats, and logging for a single serial port.
        """
        queue = self.queues[port]
        event = self.events_ready[port]

        # Prepare data file
        data_dir = Path.cwd() / "data"
        data_dir.mkdir(exist_ok=True)
        data_file = data_dir / f"serial_{port}.jsonl"
        all_data = data_dir / "all.jsonl"

        # Prepare debug logger
        debug_filename = f"{self.data_file_prefix}_{port}.debug.log"
        debug_path = Path(debug_filename)
        debug_path.parent.mkdir(parents=True, exist_ok=True)

        port_logger = logging.getLogger(f"serial.{port}")
        port_logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(debug_path, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)-5s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))

        port_logger.addHandler(fh)
        port_logger.propagate = False

        # Open serial connection
        try:
            reader, writer = await serial_asyncio.open_serial_connection(
                url=port,
                baudrate=self.baudrate
            )
        except Exception as e:
            port_logger.error(f"Failed to open {port}@{self.baudrate}: {e!r}")
            return

        port_logger.info(f"Connected to {port}@{self.baudrate}")
        event.set()

        # Start writer loop
        writer_task = asyncio.create_task(
            self.write(writer, queue, port_logger)
        )

        try:
            # Main read loop
            while not reader.at_eof():
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=self.heartbeat_interval)
                except asyncio.TimeoutError:
                    raise RuntimeError("Timeout waiting for serial data")
                if line == b"PING\n":
                    # Respond to heartbeat
                    await queue.put(b"PONG\n")
                    self.last_heartbeat[port] = time.time()
                    port_logger.info("Received PING (heartbeat)")
                    continue

                text = line.decode("utf-8", "ignore").rstrip("\r\n")

                if "available_sensors" in text:
                    payload = json.loads(text)
                    entry = {
                        "connection": {
                            "type": "serial",
                            "address": port,
                        },
                        **payload
                    }
                    with open(data_dir / "mcu_available.jsonl", 'a') as fd:
                        fd.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    continue

                try:
                    payload = json.loads(text)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    entry = {"write_time": now, **payload}
                    port_logger.info(f"Writing {entry}")
                    with (open(data_file, "a", encoding="utf-8") as df,
                          open(all_data, "a",encoding="utf-8") as ad):
                        df.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        ad.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        df.flush()
                        ad.flush()
                except json.JSONDecodeError:
                    port_logger.warning(f"Bad JSON: {text!r}")
        finally:
            await queue.put("Finish!")
            await writer_task
            writer.close()
            await writer.wait_closed()
            port_logger.info(f"Disconnected from {port}")
            self.last_heartbeat.pop(port, None)

            file_path = data_dir / "mcu_available.jsonl"
            tmp = tempfile.NamedTemporaryFile('w', delete=False, dir=file_path.parent)
            with open(file_path, 'r') as fin, tmp:
                for line in fin:
                    obj = json.loads(line)  # 或者捕获 JSONError
                    if obj.get("connection", {}).get("address") != port:
                        tmp.write(line)
            shutil.move(tmp.name, file_path)

            port_logger.removeHandler(fh)
            fh.close()
