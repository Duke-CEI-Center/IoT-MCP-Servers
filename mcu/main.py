"""
main.py - ESP32-S3 Data Uploader

This script runs on an ESP32-S3 microcontroller. It listens for commands over Wi-Fi (TCP) or UART,
executes sensor read operations (e.g., MPU6050, DHT11, KY035, DS18X20), and uploads JSON-formatted
sensor data back to the sender. Supports configurable sampling intervals, durations, and continuous streams.
"""

import uasyncio as asyncio           # MicroPython’s asyncio: async I/O for cooperative multitasking
import ujson                         # JSON encoder/decoder optimized for microcontrollers
import network                       # Wi-Fi network interface management (STA/AP modes, connections)
import sensors                       # Collection of sensor driver modules
import micropython                   # MicroPython runtime helpers (e.g., emergency exception buffer)
from time import ticks_ms            # Millisecond-resolution uptime counter (for timeouts/timestamps)
from machine import UART, Timer      # UART: serial port interface; Timer: hardware timer control
from collections import deque        # Double-ended queue for buffering incoming commands
from sensors.wiring import UART_RX, UART_TX  # Pin definitions for UART receive (RX) and transmit (TX)
import gc


# Default time (in seconds) between consecutive sensor readings
DEFAULT_INTERVAL = 2

# Wi-Fi network credentials and remote server configuration
SSID = "DukeOpen"
PASSWORD = ""
SERVER_IP = "10.194.220.224"
PORT = "9000"

# Initialize UART interface on UART1 with 115200 baud, TX pin UART_TX, RX pin UART_RX
uart = UART(1, 115200, tx=UART_TX, rx=UART_RX, timeout_char=102)

# Queues for storing parsed commands and outgoing TCP data
tcp_command = deque([], 16)  # Holds pending TCP commands: (sensor, action, interval, count)
uart_command = deque([], 16) # Holds pending UART commands
tcp_data = deque([], 128)    # Holds JSON responses to send over TCP
uart_heartbeat = deque([], 128)

# Build a dictionary mapping each sensor name to its class object
# e.g., "MPU6050" → sensors.MPU6050
SENSOR_CLASSES = {
    sensor: getattr(sensors, sensor)
    for sensor in sensors.__all__
}

# Initialize a dictionary to hold sensor instances (all start as None)
# e.g., "MPU6050" → None
all_sensors = {sensor: None for sensor in SENSOR_CLASSES}

# Dictionary storing the names of available sensors
available_sensors = {
    "available_sensors": []
}

# Stores the IDs of hardware timers that have been allocated
_used_timers = set()

peak_memory: int = 0

async def monitor_memory(interval=0.01):
    global peak_memory
    while True:
        mem_alloc = gc.mem_alloc()
        if peak_memory < mem_alloc:
            peak_memory = mem_alloc
        await asyncio.sleep(interval)

# -----------------------------------------------------------------------------
# Timer Allocation & Management
# -----------------------------------------------------------------------------
def allocate_timer(max_id=4):
    """
    Allocate and return an unused hardware timer.

    Scans IDs from 0 up to max_id-1. For the first free ID it:
      • Creates a Timer(id), deinitializes it to clear prior state,
      • Marks the ID as used,
      • Returns (timer_instance, id).

    Raises RuntimeError if no IDs are available.
    """
    for i in range(max_id):
        if i in _used_timers:
            continue
        t = Timer(i)
        t.deinit()
        _used_timers.add(i)
        return t, i
    raise RuntimeError("No free timer found")

# -----------------------------------------------------------------------------
# Sensor Manager: Initialization & Read Dispatch
# -----------------------------------------------------------------------------
async def do_read(sensor_name, action):
    """
    Dispatch a read request to the appropriate sensor module.
    Returns an awaitable yielding the sensor data (JSON/string) or an error payload.
    """
    sensor = all_sensors[sensor_name]
    if sensor is None:
        # Return JSON error if sensor type is unrecognized
        return ujson.dumps({'error': f'{sensor_name} not found'})
    try:
        return await sensor.do_read(action)
    except Exception as e:
        return ujson.dumps({'error': f'{sensor_name} failed: {e}'})

async def scan_sensors():
    """
    Scan and initialize supported sensor modules.

    For each entry in SENSOR_CLASSES, tries to instantiate the sensor:
      • On success: stores the instance in all_sensors[name] and appends name to available_sensors.
      • On failure: logs the error and sets all_sensors[name] to None.
    """
    global available_sensors
    for name, cls in SENSOR_CLASSES.items():
        try:
            sensor = cls()
            all_sensors[name] = sensor
            available_sensors["available_sensors"].append(name)
        except Exception as e:
            print(f"[Error] {name} disconnected: {e}")
            all_sensors[name] = None

# -----------------------------------------------------------------------------
# Command parsing utility
# -----------------------------------------------------------------------------
async def decode_line(line):
    """
    Parse an incoming JSON command string and extract parameters:
      - sensor : target sensor name (default: 'unknown')
      - command: operation type (e.g., 'read_temp', 'read_accel', etc.; default: 'read_all')
      - interval: seconds between each sample (default DEFAULT_INTERVAL)
      - duration: total sampling duration (0=single, >0=seconds, <0=infinite)
    Returns tuple: (sensor, action, interval_seconds, sample_count_or_None).
    """
    cmd = ujson.loads(line)
    sensor = cmd.get("sensor", "unknown")
    action = cmd.get("command", "read_all")
    interval = float(cmd.get("interval", DEFAULT_INTERVAL))
    duration = float(cmd.get("duration", 0))
    unique_id = cmd.get("id", "unknown")

    # Determine how many samples to take based on duration
    if duration == 0:
        count = 1  # Single read
    elif duration > 0:
        # Compute integer number of intervals, ensure at least one sample
        count = int(duration // interval) or 1
    else:
        count = None  # None indicates infinite streaming
    return sensor, action, interval, count, unique_id

# -----------------------------------------------------------------------------
# Wi-Fi Connection Manager
# -----------------------------------------------------------------------------
async def connect_to_wifi(ssid, password):
    """
    Connect to the specified Wi-Fi SSID as a station interface.
    Retries every second until successful, then prints allocated IP address.
    """
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()  # Reset any existing connection
    sta.active(False)
    await asyncio.sleep(1)
    sta.active(True)
    sta.connect(ssid, password)
    print('[TCP] Connecting to network...')
    while not sta.isconnected():
        await asyncio.sleep(1)
    # Print assigned IP address once connected
    print('[TCP] Allocated IP:', sta.ifconfig()[0])

# -----------------------------------------------------------------------------
# TCP Command Receiver
# -----------------------------------------------------------------------------
async def tcp_receive_command(reader, writer):
    """
    Read incoming JSON command lines over TCP, decode them, and enqueue.
    Exits on 'exit' command.
    """
    buffer = b""
    while True:
        chunk = await reader.read(8192)
        if not chunk:
            break  # Connection closed
        buffer += chunk
        lines = buffer.split(b"\n")
        buffer = lines.pop()  # Keep last partial line
        for raw in lines:
            if raw == b"PONG":
                continue
            print(f"[TCP] Timestamp: {ticks_ms()} \n"
                  f"[TCP] Received line:", raw.decode().rstrip("\r"))
        try:
            for line in lines:
                if line == b"PONG":
                    continue
                sensor, action, interval, count, unique_id = await decode_line(line)
                tcp_command.append((sensor, action, interval, count, unique_id))
                if action == "exit":
                    print("[TCP] Exiting...")
                    return
        except Exception as e:
            # On JSON parse error, respond with error payload and continue
            await writer.awrite(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            await writer.drain()
            await asyncio.sleep(0)
            continue

# -----------------------------------------------------------------------------
# TCP Response Writer
# -----------------------------------------------------------------------------
async def tcp_handle_writer(writer):
    """
    Dequeue commands and start parallel tasks for reading and writing sensor data.
    """
    while True:
        try:
            command = tcp_command.popleft()
            if not command:
                await asyncio.sleep(0)
                continue
            sensor, action, interval, count, unique_id = command
            if action == "exit":
                return  # Stop writer on exit
            # Launch tasks: one to read sensor data, another to send it
            asyncio.create_task(tcp_sensor_reader(command))
            asyncio.create_task(tcp_data_writer(writer))
        except IndexError:
            # If no pending commands, yield control briefly
            await asyncio.sleep(0)
            continue

async def tcp_data_writer(writer):
    """
    Continuously send JSON responses over TCP as they become available.
    """
    global peak_memory
    while True:
        if not tcp_data:
            await asyncio.sleep(0)
            continue
        resp = tcp_data.popleft()
        if resp is None:
            await asyncio.sleep(0)
            continue
        resp["peak_memory"] = peak_memory
        peak_memory = 0
        await writer.awrite(ujson.dumps(resp) + '\n')
        await writer.drain()

async def tcp_sensor_reader(command):
    """
    Perform sensor readings according to command parameters and enqueue JSON data.
    Loops 'count' times at 'interval' seconds, or indefinitely if count is None.
    """
    sensor, action, interval_sec, total_read_count, unique_id = command
    interval_ms = int(interval_sec * 1000)
    read_count = 0
    loop = asyncio.get_event_loop()
    done_event = asyncio.Event()
    timer, index = allocate_timer()

    # Define the async task to perform one read/write cycle
    async def _read_once():
        nonlocal read_count, timer, index, done_event, unique_id
        resp = await do_read(sensor, action)
        resp["id"] = unique_id
        tcp_data.append(resp)
        read_count += 1
        # stop when done
        if total_read_count is not None and read_count >= total_read_count:
            _used_timers.remove(index)
            timer.deinit()
            done_event.set()

    if interval_ms == 0 and total_read_count == 1:
        await _read_once()
        # Log end of session
        print("---------------------------------------------------")
        print("\t\t[TCP] DATA UPLOADED!")
        print("---------------------------------------------------")
        return

    # Schedule callback pushed from timer interrupt into main thread
    def _callback(dummy):
        loop.create_task(_read_once())

    # Allocate and init the hardware/soft timer
    timer.init(
        period=interval_ms,
        mode=Timer.PERIODIC,
        callback=lambda t: micropython.schedule(_callback, 0)
    )

    # Wait until all reads complete
    await done_event.wait()


    # Log end of session
    print("---------------------------------------------------")
    print("\t\t[TCP] DATA UPLOADED!")
    print("---------------------------------------------------")

async def tcp_send_heartbeat(writer):
    """
    Sending Heartbeat message to Server.

    Every 5 seconds:
      • Sends a "PING" message over TCP to solicit the next heartbeat.
    """
    while True:
        await writer.awrite(b"PING\n")
        await asyncio.sleep(5.0)

# -----------------------------------------------------------------------------
# Complete TCP Session Handler
# -----------------------------------------------------------------------------
async def handle_tcp(reader, writer):
    """
    Manage a full TCP session: concurrently reading commands and writing responses.
    """
    reader_task = asyncio.create_task(tcp_receive_command(reader, writer))
    writer_task = asyncio.create_task(tcp_handle_writer(writer))
    heartbeat_task = asyncio.create_task(tcp_send_heartbeat(writer))
    monitor_task = asyncio.create_task(monitor_memory())
    await asyncio.gather(reader_task, writer_task, heartbeat_task, monitor_task)

async def tcp_connect():
    """
    Establish a TCP connection to the remote server, retrying on failure.
    Returns (reader, writer) on success.
    """
    try:
        print(f"[TCP] Connecting to server IP: {SERVER_IP} port: {PORT} ...")
        reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
        # Send a null byte to confirm connection
        await writer.awrite(ujson.dumps(available_sensors) + '\n')
        await writer.drain()
        print(f"[TCP] Connection established!")
        return reader, writer
    except OSError as e:
        print(f"[TCP] Failed to connect to server: {e}")
        # noinspection PyUnboundLocalVariable
        await reader.aclose()
        await writer.aclose()
        await asyncio.sleep(0)

# -----------------------------------------------------------------------------
# TCP Worker Entry Point
# -----------------------------------------------------------------------------
async def tcp_worker():
    """
    Maintain Wi-Fi and TCP connections, handing off to session handler.
    Retries on failures indefinitely.
    """
    global SSID, PASSWORD, SERVER_IP, PORT
    try:
        await asyncio.wait_for(connect_to_wifi(SSID, PASSWORD), timeout=10)
    except asyncio.TimeoutError:
        print(f"[TCP] Wi-Fi connection failed! Worker killed.")
        return

    while True:
        try:
            reader, writer = await tcp_connect()
            await handle_tcp(reader, writer)
            print("[TCP] Disconnecting from server...")
            reader.close()
            writer.close()
            await asyncio.sleep(0)
        except TypeError: pass
        except Exception as e:
            print("[TCP] Worker error:", e)
            try:
                await reader.aclose()
                await writer.aclose()
            except TypeError: pass
            await asyncio.sleep(0)

# -----------------------------------------------------------------------------
# UART Command Receiver/Writer
# -----------------------------------------------------------------------------
async def uart_receive_command():
    """
    Read fragmented JSON commands from UART, buffer until newline, parse, and enqueue.
    """
    buffer = b""
    while True:
        if uart.any():
            data = uart.read(uart.any())
            buffer += data

            # Process all complete lines terminated by '\n'
            while b"\n" in buffer:
                line, _, buffer = buffer.partition(b"\n")
                if line == b"PONG": break
                print(f"[Serial] Timestamp: {ticks_ms()} \n"
                      f"[Serial] Received line: {line}")
                try:
                    sensor, action, interval, count, unique_id = await decode_line(line)
                    uart_command.append((sensor, action, interval, count, unique_id))
                except Exception as e:
                    # Respond with JSON error on parse failure
                    err = {"error": f"bad json: {e}"}
                    uart.write(ujson.dumps(err).encode('utf-8') + b"\n")
        # Yield control to allow other tasks to run
        await asyncio.sleep(0)

async def uart_handle_writer():
    """
    Dequeue UART commands and launch tasks to send sensor data back over serial.
    """
    while True:
        try:
            command = uart_command.popleft()
            if not command:
                await asyncio.sleep(0)
                continue
            sensor, action, interval, count, unique_id = command
            if action == "exit":
                print("[Serial] Received exit — stopping current stream")
                continue
            asyncio.create_task(uart_write(command))
        except IndexError:
            await asyncio.sleep(0)
            continue
        except Exception as e:
            print(e)
            await asyncio.sleep(0)
            continue

async def uart_write(command):
    """
    Send sensor readings over UART according to command parameters.
    """
    sensor, action, interval_sec, total_read_count, unique_id = command
    interval_ms = int(interval_sec * 1000)
    read_count = 0
    loop = asyncio.get_event_loop()
    done_event = asyncio.Event()
    timer, index = allocate_timer()

    # Define the async task to perform one read/write cycle
    async def _read_once():
        nonlocal read_count, done_event, timer, index, unique_id
        resp = await do_read(sensor, action)
        resp["id"] = unique_id
        uart.write(ujson.dumps(resp).encode('utf-8') + b'\n')
        uart.flush()
        read_count += 1
        # stop when done
        if total_read_count is not None and read_count >= total_read_count:
            _used_timers.remove(index)
            timer.deinit()
            done_event.set()

    if interval_ms == 0 and total_read_count == 1:
        await _read_once()
        # Log end of session
        print("---------------------------------------------------")
        print("\t\t[Serial] DATA UPLOADED!")
        print("---------------------------------------------------")
        return

    # Schedule callback pushed from timer interrupt into main thread
    def _callback(dummy):
        loop.create_task(_read_once())

    # Allocate and init the hardware/soft timer
    timer.init(
        period=interval_ms,
        mode=Timer.PERIODIC,
        callback=lambda t: micropython.schedule(_callback, 0)
    )

    # Wait until all reads complete
    await done_event.wait()

    # Indicate completion of UART data stream
    print("---------------------------------------------------")
    print("\t\t[Serial] DATA UPLOADED!")
    print("---------------------------------------------------")

# -----------------------------------------------------------------------------
# UART Connection Handler
# -----------------------------------------------------------------------------
async def uart_connect():
    while True:
        uart.write(b"PING\n")
        uart.flush()
        if uart.any():
            line = uart.readline()
            if line == b"PONG\n":
                return
        await asyncio.sleep(5.0)

async def uart_send_heartbeat():
    """
    Sending Heartbeat message to Server.

    Every 5 seconds:
      • Sends a "PING" message over UART to solicit the next heartbeat.
    """
    while True:
        uart.write(b"PING\n")
        await asyncio.sleep(5.0)

# -----------------------------------------------------------------------------
# UART Worker Entry Point
# -----------------------------------------------------------------------------
async def uart_worker():
    """
    Start UART reader and writer tasks and monitor for exceptions.
    """
    print("[Serial] Connecting to server...")
    await uart_connect()
    try:
        print('[Serial] UART connection established!')
        uart.write(ujson.dumps(available_sensors) + '\n')
        reader_task = asyncio.create_task(uart_receive_command())
        writer_task = asyncio.create_task(uart_handle_writer())
        heartbeat_task = asyncio.create_task(uart_send_heartbeat())
        await asyncio.gather(reader_task, writer_task, heartbeat_task)
    except Exception as e:
        print("[Serial] Worker error:", e)

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
async def main():
    """
    Detect available sensors, then launch both TCP and UART workers concurrently.
    """
    await scan_sensors()
    print(f"Found existing sensors: {available_sensors['available_sensors']}")
    tcp_task = asyncio.create_task(tcp_worker())
    uart_task = asyncio.create_task(uart_worker())
    await asyncio.gather(tcp_task, uart_task)

# Execute main() when script is run directly
if __name__ == '__main__':
    asyncio.run(main())

