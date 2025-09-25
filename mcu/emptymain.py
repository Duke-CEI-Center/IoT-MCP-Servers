"""
main.py - ESP32-S3 Data Uploader (Modified for No-Load Testing)

This modified script runs on an ESP32-S3 microcontroller. It listens for commands over Wi-Fi (TCP) or UART,
detects and reports available sensors, but instead of executing sensor operations, it directly returns 
timestamp and peak memory usage information to measure program latency and memory overhead under no-load conditions.
"""

import uasyncio as asyncio           # MicroPython's asyncio: async I/O for cooperative multitasking
import ujson                         # JSON encoder/decoder optimized for microcontrollers
import network                       # Wi-Fi network interface management (STA/AP modes, connections)
import sensors                       # Collection of sensor driver modules
import micropython                   # MicroPython runtime helpers (e.g., emergency exception buffer)
from time import ticks_ms            # Millisecond-resolution uptime counter (for logging only)
from machine import UART, Timer      # UART: serial port interface; Timer: hardware timer control
from collections import deque        # Double-ended queue for buffering incoming commands
from sensors.wiring import UART_RX, UART_TX  # Pin definitions for UART receive (RX) and transmit (TX)
import gc


# Default time (in seconds) between consecutive responses
DEFAULT_INTERVAL = 2

# Wi-Fi network credentials and remote server configuration
SSID = "DukeOpen"
PASSWORD = ""
SERVER_IP = "10.194.220.224"
PORT = "9000"

# Initialize UART interface on UART1 with 115200 baud, TX pin UART_TX, RX pin UART_RX
uart = UART(1, 115200, tx=UART_TX, rx=UART_RX, timeout_char=102)

# Queues for storing parsed commands and outgoing data
tcp_command = deque([], 16)  # Holds pending TCP commands
uart_command = deque([], 16) # Holds pending UART commands
tcp_data = deque([], 128)    # Holds JSON responses to send over TCP

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
    """Monitor peak memory usage continuously"""
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
# Sensor Manager: Detection (No actual reading in no-load mode)
# -----------------------------------------------------------------------------
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
            print(f"[Sensor] {name} detected and initialized")
        except Exception as e:
            print(f"[Error] {name} disconnected: {e}")
            all_sensors[name] = None

# -----------------------------------------------------------------------------
# No-Load Response Generator
# -----------------------------------------------------------------------------
async def generate_no_load_response(sensor_name, action, unique_id):
    """
    Generate a simplified no-load response with only ID and peak memory.
    This replaces the actual sensor reading functionality.
    """
    global peak_memory
    
    # Create minimal response data
    response_data = {
        "id": unique_id,
        "peak_memory": peak_memory
    }
    
    # Reset peak memory after reporting
    peak_memory = 0
    
    return response_data

# -----------------------------------------------------------------------------
# Command parsing utility
# -----------------------------------------------------------------------------
async def decode_line(line):
    """
    Parse an incoming JSON command string and extract parameters.
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
    Dequeue commands and start parallel tasks for generating and writing no-load responses.
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
            # Launch tasks: one to generate no-load data, another to send it
            asyncio.create_task(tcp_no_load_generator(command))
            asyncio.create_task(tcp_data_writer(writer))
        except IndexError:
            # If no pending commands, yield control briefly
            await asyncio.sleep(0)
            continue

async def tcp_data_writer(writer):
    """
    Continuously send JSON responses over TCP as they become available.
    """
    while True:
        if not tcp_data:
            await asyncio.sleep(0)
            continue
        resp = tcp_data.popleft()
        if resp is None:
            await asyncio.sleep(0)
            continue
        await writer.awrite(ujson.dumps(resp) + '\n')
        await writer.drain()

async def tcp_no_load_generator(command):
    """
    Generate no-load responses according to command parameters and enqueue JSON data.
    """
    sensor, action, interval_sec, total_read_count, unique_id = command
    interval_ms = int(interval_sec * 1000)
    read_count = 0
    loop = asyncio.get_event_loop()
    done_event = asyncio.Event()
    timer, index = allocate_timer()

    # Define the async task to perform one response generation cycle
    async def _generate_once():
        nonlocal read_count, timer, index, done_event, unique_id
        resp = await generate_no_load_response(sensor, action, unique_id)
        tcp_data.append(resp)
        read_count += 1
        # stop when done
        if total_read_count is not None and read_count >= total_read_count:
            _used_timers.remove(index)
            timer.deinit()
            done_event.set()

    if interval_ms == 0 and total_read_count == 1:
        await _generate_once()
        # Log end of session
        print("---------------------------------------------------")
        print("\t\t[TCP] NO-LOAD DATA UPLOADED!")
        print("---------------------------------------------------")
        return

    # Schedule callback pushed from timer interrupt into main thread
    def _callback(dummy):
        loop.create_task(_generate_once())

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
    print("\t\t[TCP] NO-LOAD DATA UPLOADED!")
    print("---------------------------------------------------")

async def tcp_send_heartbeat(writer):
    """
    Send heartbeat message to server every 5 seconds.
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
    Establish a TCP connection to the remote server.
    """
    try:
        print(f"[TCP] Connecting to server IP: {SERVER_IP} port: {PORT} ...")
        reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
        # Send initial message to confirm connection
        await writer.awrite(ujson.dumps(available_sensors) + '\n')
        await writer.drain()
        print(f"[TCP] Connection established!")
        return reader, writer
    except OSError as e:
        print(f"[TCP] Failed to connect to server: {e}")
        await asyncio.sleep(0)

# -----------------------------------------------------------------------------
# TCP Worker Entry Point
# -----------------------------------------------------------------------------
async def tcp_worker():
    """
    Maintain Wi-Fi and TCP connections, handling session.
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
        except TypeError:
            pass
        except Exception as e:
            print("[TCP] Worker error:", e)
            try:
                await reader.aclose()
                await writer.aclose()
            except TypeError:
                pass
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
                if line == b"PONG":
                    break
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
    Dequeue UART commands and launch tasks to send no-load data back over serial.
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
    Send no-load responses over UART according to command parameters.
    """
    sensor, action, interval_sec, total_read_count, unique_id = command
    interval_ms = int(interval_sec * 1000)
    read_count = 0
    loop = asyncio.get_event_loop()
    done_event = asyncio.Event()
    timer, index = allocate_timer()

    # Define the async task to perform one response generation cycle
    async def _generate_once():
        nonlocal read_count, done_event, timer, index, unique_id
        resp = await generate_no_load_response(sensor, action, unique_id)
        uart.write(ujson.dumps(resp).encode('utf-8') + b'\n')
        uart.flush()
        read_count += 1
        # stop when done
        if total_read_count is not None and read_count >= total_read_count:
            _used_timers.remove(index)
            timer.deinit()
            done_event.set()

    if interval_ms == 0 and total_read_count == 1:
        await _generate_once()
        # Log end of session
        print("---------------------------------------------------")
        print("\t\t[Serial] NO-LOAD DATA UPLOADED!")
        print("---------------------------------------------------")
        return

    # Schedule callback pushed from timer interrupt into main thread
    def _callback(dummy):
        loop.create_task(_generate_once())

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
    print("\t\t[Serial] NO-LOAD DATA UPLOADED!")
    print("---------------------------------------------------")

# -----------------------------------------------------------------------------
# UART Connection Handler
# -----------------------------------------------------------------------------
async def uart_connect():
    """Wait for UART connection handshake"""
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
    Send heartbeat message over UART every 5 seconds.
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
    Detect available sensors, then launch both TCP and UART workers concurrently in no-load test mode.
    """
    print("="*60)
    print("ESP32-S3 NO-LOAD TEST MODE")
    print("This version skips sensor operations and returns")
    print("timing and memory information for latency testing.")
    print("="*60)
    
    await scan_sensors()
    print(f"Found existing sensors: {available_sensors['available_sensors']}")
    
    tcp_task = asyncio.create_task(tcp_worker())
    uart_task = asyncio.create_task(uart_worker())
    await asyncio.gather(tcp_task, uart_task)

# Execute main() when script is run directly
if __name__ == '__main__':
    asyncio.run(main())