import asyncio
import json
import os
import time
from typing import List, Dict

import serial
import serial.tools.list_ports
from mcp.server.fastmcp import FastMCP

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DATA_FILE_TCP    = os.path.join(os.path.dirname(__file__), 'tmp36_data_tcp.csv')
DATA_FILE_SERIAL = os.path.join(os.path.dirname(__file__), 'tmp36_data_serial.csv')
TCP_HOST         = '0.0.0.0'
TCP_PORT         = 9002
SERIAL_BAUD      = 115200

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------
reader_tcp: asyncio.StreamReader = None
writer_tcp: asyncio.StreamWriter = None
ser = None

queue_tcp: asyncio.Queue   = asyncio.Queue()
queue_serial: asyncio.Queue = asyncio.Queue()

event_tcp_ready    = asyncio.Event()
event_serial_ready = asyncio.Event()

# Ensure data files exist
for path in (DATA_FILE_TCP, DATA_FILE_SERIAL):
    with open(path, 'a', encoding='utf-8'):
        pass

# -----------------------------------------------------------------------------
# TCP Transport Tasks
# -----------------------------------------------------------------------------
async def tcp_server():
    """Start TCP server and accept a single TMP36 connection."""
    async def handle_conn(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        global reader_tcp, writer_tcp
        reader_tcp, writer_tcp = r, w
        event_tcp_ready.set()
        addr = w.get_extra_info('peername')
        print(f'[TCP] TMP36 connected from {addr}')

    server = await asyncio.start_server(handle_conn, TCP_HOST, TCP_PORT)
    print(f'[TCP] Listening on {TCP_HOST}:{TCP_PORT}')
    async with server:
        await server.serve_forever()

async def reader_tcp_loop():
    """Continuously read lines from TCP and append to DATA_FILE_TCP."""
    await event_tcp_ready.wait()
    while True:
        line = await reader_tcp.readline()
        if not line:
            await asyncio.sleep(0.01)
            continue
        text = line.decode('utf-8').rstrip()
        with open(DATA_FILE_TCP, 'a', encoding='utf-8') as f:
            f.write(text + '\n')

async def writer_tcp_loop():
    """Send queued JSON commands over TCP to the TMP36 MCU."""
    await event_tcp_ready.wait()
    while True:
        msg = await queue_tcp.get()
        writer_tcp.write((msg.rstrip() + '\n').encode())
        await writer_tcp.drain()

# -----------------------------------------------------------------------------
# Serial Transport Tasks
# -----------------------------------------------------------------------------
async def serial_connection(port_name: str = None):
    """Open and prepare the serial port for TMP36 communication."""
    global ser
    if port_name is None:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            raise RuntimeError("No serial ports found")
        port_name = ports[0].device
    print(f'[Serial] Opening {port_name}@{SERIAL_BAUD}')
    ser = serial.Serial(port_name, SERIAL_BAUD, timeout=1)
    event_serial_ready.set()

async def reader_serial_loop():
    """Continuously read lines from serial and append to DATA_FILE_SERIAL."""
    await event_serial_ready.wait()
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, ser.readline)
        if not line:
            continue
        text = line.decode('utf-8').rstrip()
        with open(DATA_FILE_SERIAL, 'a', encoding='utf-8') as f:
            f.write(text + '\n')

async def writer_serial_loop():
    """Send queued JSON commands over serial to the TMP36 MCU."""
    await event_serial_ready.wait()
    while True:
        msg = await queue_serial.get()
        ser.write((msg.rstrip() + '\n').encode())

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
async def send_command(cmd: Dict, transport: str = 'wifi') -> None:
    """
    Queue a JSON command for the specified transport.

    Parameters:
    - cmd: the command dictionary to send
    - transport: 'wifi' to use TCP, 'serial' to use serial port
    """
    msg = json.dumps(cmd)
    if transport == 'wifi':
        await queue_tcp.put(msg)
    else:
        await queue_serial.put(msg)


def read_new_data(file_path: str, timeout: float = None) -> List[Dict]:
    """
    Poll the given data file for new JSON lines up to timeout seconds.
    Returns a list of parsed JSON objects (or raw strings on parse error).
    """
    start = time.time()
    init_size = os.path.getsize(file_path)
    while True:
        if os.path.getsize(file_path) > init_size:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.seek(init_size)
                lines = [l.strip() for l in f.readlines() if l.strip()]
            results = []
            for l in lines:
                try:
                    results.append(json.loads(l))
                except json.JSONDecodeError:
                    results.append({'raw': l})
            return results
        if timeout is not None and time.time() - start > timeout:
            return []
        time.sleep(0.1)

# -----------------------------------------------------------------------------
# MCP Server and Tool for TMP36
# -----------------------------------------------------------------------------
mcp = FastMCP(
    "TMP36",
    description="TMP36 temperature monitoring via MCP"
)

@mcp.tool()
async def read_temp(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[float]:
    """
    Read temperature values from the TMP36 sensor.

    Parameters:
    - interval: time between readings in seconds. Default 0.0 returns a single reading.
    - duration: total duration in seconds for continuous readings (0.0 => single reading;
      >0.0 => readings over duration; <0.0 => continuous until stopped).
    - transport: 'wifi' to use TCP, 'serial' to use serial port.

    Returns:
    A list of temperature readings in degrees Celsius.
    """
    cmd = {"command": "read_temp", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    data = read_new_data(file_path, timeout=(duration or 1.0))
    return [item['temperature'] for item in data if 'temperature' in item]

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    # start transports
    loop.create_task(tcp_server())
    loop.create_task(reader_tcp_loop())
    loop.create_task(writer_tcp_loop())
    loop.create_task(serial_connection())
    loop.create_task(reader_serial_loop())
    loop.create_task(writer_serial_loop())
    mcp.run()
