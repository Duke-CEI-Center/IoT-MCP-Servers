import asyncio
import json
import logging
import os
import ctypes
import uuid
import time
from datetime import datetime
from pathlib import Path
from aiohttp import web
from importlib import import_module
import yaml
import shutil

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CONFIG_PATH = 'config.yaml'
SERVER_IP = 'localhost'
SERVER_PORT = 8000

# -----------------------------------------------------------------------------
# HTTP Server Core
# -----------------------------------------------------------------------------
routes = web.RouteTableDef()

# Holds mapping from connection type to Transport instance
transport_registry: dict[str, object] = {}

def find_connection_for_sensor(sensor_name, filepath='data/mcu_available.jsonl'):
    """
    Read a JSONL file line by line, parse each line as a connection dict,
    and return the first connection whose sensors list includes the requested sensor.
    """
    # Determine sensor name (if request_sensor is a dict with a 'name' key)

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines

            try:
                conn = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip lines that are not valid JSON

            sensors = conn.get('available_sensors', [])
            if sensor_name in sensors:
                return conn.get('connection')  # return the first matching connection

    # Return None or an empty dict if no matching connection is found
    return None

def _is_sensor_cmd(cmd: dict) -> bool:
    if set(cmd.keys()) != {"sensor", "command", "interval", "duration"}:
        return False
    return find_connection_for_sensor(cmd["sensor"]) is not None

def _is_timed_cmd(cmd: dict, fmt: str = "%Y-%m-%d %H:%M:%S") -> bool:
    if set(cmd.keys()) != {"start","end","interval","request"}:
        return False
    if not _is_sensor_cmd(cmd["request"]):
        return False

    try:
        start_time = datetime.strptime(cmd["start"], fmt)
        end_time = datetime.strptime(cmd["end"], fmt)
        return end_time >= start_time > datetime.now()
    except ValueError:
        return False

@routes.post('/send_cmd')
async def handle_send_cmd(request):
    """
    Expected JSON body:
    {
      "sensor": "...", "command": {...}, "interval": 1.0, "duration": 10.0
    }
    or
    {
      "start": "...", "end": "...", "interval": 1.0, "request": {...}
    }
    """
    try:
        cmd = await request.json()
    except Exception:
        server_logger.warning("Invalid JSON body")
        return web.Response(status=400, text="Invalid JSON")

    # Single commands in the two supported formats
    if not (_is_sensor_cmd(cmd) or _is_timed_cmd(cmd)):
        server_logger.warning("Bad command format or sensor unavailable: %r", cmd)
        return web.Response(status=400, text="Invalid command format or sensor unavailable")

    # Dispatch the command in background
    unique_id = str(uuid.uuid4())
    asyncio.create_task(decode_and_dispatch_command(cmd, unique_id))

    server_logger.info(f"Accept client request: {cmd}")
    return web.json_response({"status": "accept", "id": unique_id})

async def decode_and_dispatch_command(cmd: dict, unique_id: str, fmt: str = "%Y-%m-%d %H:%M:%S"):
    if _is_sensor_cmd(cmd):
        cmd["id"] = unique_id
        asyncio.create_task(dispatch_command(cmd))

    elif _is_timed_cmd(cmd):
        cmd["id"] = unique_id
        start: datetime = datetime.strptime(cmd['start'], fmt)
        end: datetime = datetime.strptime(cmd['end'], fmt)
        interval: float = float(cmd['interval'])
        duration = (end - start).total_seconds()
        request: dict = cmd['request']
        request['duration'] = duration
        request['interval'] = interval
        asyncio.create_task(dispatch_command(request, start_time= start))

    else: raise RuntimeError(f"Unknown command: {cmd}")


async def dispatch_command(cmd: dict, start_time: datetime = None):
    try:
        if start_time is None:
            await dispatch(cmd)
            return

        ctypes.windll.winmm.timeBeginPeriod(1)

        delay = (start_time - datetime.now()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay-1)

        await dispatch(cmd)

    except Exception as e:
        server_logger.warning("Failed to dispatch command: %r", e)

    finally:
        ctypes.windll.winmm.timeEndPeriod(1)

async def dispatch(cmd: dict):
    request_sensor = cmd.get('sensor') or {}
    connection = find_connection_for_sensor(request_sensor)
    conn_type = connection.get('type')
    address = connection.get('address')

    transport = transport_registry.get(conn_type)
    # Prepare payload without connection info
    payload = {k: v for k, v in cmd.items() if k != 'connection'}
    msg = json.dumps(payload).encode('utf-8')

    # Delegate to transport
    await transport.send(msg, address)

# -----------------------------------------------------------------------------
# Startup Logic
# -----------------------------------------------------------------------------
async def start_servers():
    # Load transports from config
    cfg = yaml.safe_load(open(CONFIG_PATH))
    for t in cfg.get('transports', []):
        module = import_module(t['module'])
        cls = getattr(module, t['class'])
        args = t.get('args', {})
        instance = cls(**args)
        transport_registry[t['type']] = instance
        # Launch transport open/init (must implement open())
        asyncio.create_task(instance.open())
        server_logger.debug(f'Loaded transport: {t["type"]}')

    # Optional: start global monitor
    monitor_cfg = cfg.get('monitor', {})
    if monitor_cfg.get('enabled', False):
        timeout = monitor_cfg.get('timeout', 10)
        interval = monitor_cfg.get('interval', 5)
        asyncio.create_task(_monitor_loop(timeout, interval))

    # Start HTTP server
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=SERVER_IP, port=SERVER_PORT)
    await site.start()
    server_logger.info(f'HTTP server running at http://{SERVER_IP}:{SERVER_PORT}')

async def _monitor_loop(timeout: int, interval: int):
    """Global heartbeat monitor (optional)"""
    while True:
        now = time.time()
        for conn_type, transport in transport_registry.items():
            # Each transport should expose last_heartbeat mapping
            hb = getattr(transport, 'last_heartbeat', {})
            for addr, ts in hb.items():
                if now - ts > timeout - 3:
                    server_logger.warning(
                        f'{conn_type}@{addr} missed heartbeat ({now - ts:.1f}s)'
                    )
                    server_logger.warning(
                        f'{conn_type}@{addr} will be killed if missing heartbeat for {timeout:.1f}s)'
                    )
        await asyncio.sleep(interval)

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
def get_server_logger(log_path: str = 'logs/server.log') -> logging.Logger:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('server')
    logger.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path)
               for h in logger.handlers):
        fh = logging.FileHandler(log_path, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)-5s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(fh)
    logger.propagate = False
    return logger

def get_access_logger(log_path: str = 'logs/access.log') -> logging.Logger:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('aiohttp.access')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)-5s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(fh)
    return logger

def delete_dirs(*dirs):
    """
    Recursively delete each specified directory and all of its contents.
    """
    for d in dirs:
        folder = Path(d)
        if folder.exists() and folder.is_dir():
            try:
                shutil.rmtree(folder)
            except Exception:
                pass
        else:
            pass

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    delete_dirs("data", "logs")
    Path('data').mkdir(parents=True, exist_ok=True)
    Path('data/mcu_available.jsonl').touch()
    server_logger = get_server_logger()
    access_logger = get_access_logger()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_servers())
        loop.run_forever()
    except KeyboardInterrupt:
        server_logger.info('Shutting down...')
    finally:
        loop.close()
