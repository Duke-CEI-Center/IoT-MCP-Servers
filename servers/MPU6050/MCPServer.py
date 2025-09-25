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
DATA_FILE_TCP = os.path.join(os.path.dirname(__file__), 'data_tcp.csv')
DATA_FILE_SERIAL = os.path.join(os.path.dirname(__file__), 'data_serial.csv')
TCP_HOST = '0.0.0.0'
TCP_PORT = 9000
SERIAL_BAUD = 115200

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------
reader_tcp: asyncio.StreamReader
writer_tcp: asyncio.StreamWriter
ser: serial.Serial

queue_tcp: asyncio.Queue = asyncio.Queue()
queue_serial: asyncio.Queue = asyncio.Queue()

event_tcp_ready = asyncio.Event()
event_serial_ready = asyncio.Event()

# Ensure data files exist
for fpath in (DATA_FILE_TCP, DATA_FILE_SERIAL):
    with open(fpath, 'a', encoding='utf-8'):
        pass

# -----------------------------------------------------------------------------
# Background Tasks for TCP transport
# -----------------------------------------------------------------------------
async def tcp_server():
    """Start a TCP server and accept a single ESP32 connection."""
    async def handle_conn(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        global reader_tcp, writer_tcp
        reader_tcp, writer_tcp = r, w
        event_tcp_ready.set()
        addr = w.get_extra_info('peername')
        print(f'[TCP] Connected from {addr}')

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
    """Send queued JSON commands over TCP to the ESP32."""
    await event_tcp_ready.wait()
    while True:
        msg = await queue_tcp.get()
        writer_tcp.write((msg.rstrip() + '\n').encode())
        await writer_tcp.drain()

# -----------------------------------------------------------------------------
# Background Tasks for Serial transport
# -----------------------------------------------------------------------------
async def serial_connection(port_name: str = None):
    """Open and prepare the serial port for ESP32 communication."""
    global ser
    if port_name is None:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            raise RuntimeError("No serial ports found")
        for port in ports:
            port_name = port.device
            try:
                ser = serial.Serial(port_name, SERIAL_BAUD, timeout=1)
                print(f'[Serial] Opening {port_name}@{SERIAL_BAUD}')
                event_serial_ready.set()
                return
            except Exception as e:
                print(f"[Serial] {port_name} failed to open: {e}")
    else:
        print(f'[Serial] Opening {port_name}@{SERIAL_BAUD}')
        try:
            ser = serial.Serial(port_name, SERIAL_BAUD, timeout=1)
            event_serial_ready.set()
            return
        except Exception as e:
            print(f"[Serial] {port_name} failed to open: {e}")

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
    """Send queued JSON commands over serial to the ESP32."""
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
    - transport: 'Wi-Fi' to use TCP, 'serial' to use serial port
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
# MCP Server and Tools (with original description preserved)
# -----------------------------------------------------------------------------
mcp = FastMCP(
    "ESP32",
    description="ESP32 PC data monitoring via MCP"
)

@mcp.tool()
async def read_temperature(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[float]:
    """
    Read temperature values from the MPU6050 sensor.

    Parameters:
    - interval: time between readings in seconds. Default 0.0 returns a single reading.
    - duration: total duration in seconds for continuous readings (0.0 => single reading;
      >0.0 => readings over duration; <0.0 => continuous until stopped).
    - transport: 'Wi-Fi' to use TCP, 'serial' to use serial port.

    Returns:
    A list of temperature readings in degrees Celsius.
    """
    cmd = {"command": "read_temp", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    data = read_new_data(file_path, timeout=(duration or 1.0))
    return [item['temperature'] for item in data if 'temperature' in item]

@mcp.tool()
async def read_humidity(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[float]:
    """
    Read humidity values from the MPU6050 sensor.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds for continuous readings.
    - transport: 'Wi-Fi' or 'serial'.

    Returns:
    A list of humidity readings in percentage.
    """
    cmd = {"command": "read_humidity", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    data = read_new_data(file_path, timeout=(duration or 1.0))
    return [item['humidity'] for item in data if 'humidity' in item]

@mcp.tool()
async def read_accel(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[float]:
    """
    Read accelerometer values from the sensor.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds.
    - transport: 'Wi-Fi' or 'serial'.

    Returns:
    A list of acceleration readings.
    """
    cmd = {"command": "read_accel", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    data = read_new_data(file_path, timeout=(duration or 1.0))
    return [item['accel'] for item in data if 'accel' in item]

@mcp.tool()
async def read_gyro(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[float]:
    """
    Read gyroscope values from the sensor.

    Parameters:
    - interval: time between readings.
    - duration: total duration.
    - transport: 'Wi-Fi' or 'serial'.

    Returns:
    A list of gyroscope readings.
    """
    cmd = {"command": "read_gyro", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    data = read_new_data(file_path, timeout=(duration or 1.0))
    return [item['gyro'] for item in data if 'gyro' in item]

@mcp.tool()
async def read_tilt(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[float]:
    """
    Read tilt values from the sensor.

    Parameters:
    - interval: time between readings.
    - duration: total duration.
    - transport: 'Wi-Fi' or 'serial'.

    Returns:
    A list of tilt readings.
    """
    cmd = {"command": "read_tilt", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    data = read_new_data(file_path, timeout=(duration or 1.0))
    return [item['tilt'] for item in data if 'tilt' in item]

@mcp.tool()
async def read_all(
    interval: float = 0.0,
    duration: float = 0.0,
    transport: str = 'wifi'
) -> List[Dict[str, float]]:
    """
    Read all sensor values (temperature, humidity, accel, gyro, tilt).

    Parameters:
    - interval: time between readings.
    - duration: total duration.
    - transport: 'Wi-Fi' or 'serial'.

    Returns:
    A list of dicts containing all sensor readings.
    """
    cmd = {"command": "read_all", "interval": interval, "duration": duration}
    await send_command(cmd, transport)
    file_path = DATA_FILE_TCP if transport == 'wifi' else DATA_FILE_SERIAL
    return read_new_data(file_path, timeout=(duration or 1.0))

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    # Start both TCP and serial transports in parallel
    loop.create_task(tcp_server())
    loop.create_task(reader_tcp_loop())
    loop.create_task(writer_tcp_loop())
    loop.create_task(serial_connection())
    loop.create_task(reader_serial_loop())
    loop.create_task(writer_serial_loop())
    mcp.run()
