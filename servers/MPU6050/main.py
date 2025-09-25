'''
main.py - ESP32S3 MPU6050 Data Uploader

This script runs on an ESP32-S3, connecting via Wi-Fi or UART to receive commands
and upload sensor data (accelerometer, gyroscope, temperature, tilt) from an MPU6050.
'''

import uasyncio as asyncio  # Asynchronous IO library for microcontrollers
from machine import Pin, SoftI2C, UART  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp
from mpu6050 import MPU6050  # MPU6050 sensor driver
import ujson, network  # JSON handling and network interface

# -----------------------------------------------------------------------------
# Hardware initialization
# -----------------------------------------------------------------------------
# Initialize I2C bus (SCL=Pin 7, SDA=Pin 6, frequency=100kHz)
i2c = SoftI2C(scl=Pin(7), sda=Pin(6), freq=100000)
# Create MPU6050 sensor instance
mpu6050 = MPU6050(i2c)

# Initialize UART interface (UART1, baudrate=115200, TX=Pin5, RX=Pin4)
uart = UART(1, 115200, tx=5, rx=4, timeout_char=100)

# Default sampling interval (seconds)
DEFAULT_INTERVAL = 2

# Wi-Fi and server configuration (to be set in config.py or here)
SSID = "<SSID>"
PASSWORD = "<PASSWORD>"
SERVER_IP = "<SERVER_IP>"
PORT = "<PORT>"

# -----------------------------------------------------------------------------
# Sensor read helper
# -----------------------------------------------------------------------------
def mpu6050_read(action):
    """
    Read data from the MPU6050 sensor based on action:
      - read_temp: return temperature only
      - read_accel: return accelerometer data only
      - read_gyro: return gyroscope data only
      - read_angle: return tilt/angle data only
      - any other: return all available sensor data
    Returns a dict with a timestamp and requested fields, or an error.
    """
    global mpu6050
    try:
        acc = mpu6050.read_accel_data()      # {'x':..., 'y':..., 'z':...}
        gyro = mpu6050.read_gyro_data()      # {'x':..., 'y':..., 'z':...}
        temp = mpu6050.read_temperature()    # float in °C
        angle = mpu6050.read_angle()         # {'x':pitch, 'y':roll}
    except Exception as e:
        # Return error with timestamp if reading fails
        return {"timestamp": ticks_ms(), "error": str(e)}

    # Build response based on requested action
    ts = ticks_ms()
    if action == "read_temp":
        return {"timestamp": ts, "temperature": temp}
    elif action == "read_accel":
        return {"timestamp": ts, "accel": acc}
    elif action == "read_gyro":
        return {"timestamp": ts, "gyro": gyro}
    elif action == "read_angle":
        return {"timestamp": ts, "tilt": angle}
    else:
        # Default: return all data
        return {
            "timestamp": ts,
            "accel": acc,
            "gyro": gyro,
            "temperature": temp,
            "tilt": angle
        }

# -----------------------------------------------------------------------------
# Command parsing helper
# -----------------------------------------------------------------------------
def get_instruction(line):
    """
    Parse a JSON command string from server/UART.
    Expected fields:
      - command: one of read_temp, read_accel, read_gyro, read_angle, read_all (default)
      - interval: seconds between readings (default DEFAULT_INTERVAL)
      - duration: total duration to read; 0 for single, >0 for total seconds, <0 for infinite
    Returns tuple: (full_cmd_dict, action, interval_sec, count)
    """
    cmd = ujson.loads(line)
    action = cmd.get("command", "read_all")           # Read command type
    interval = float(cmd.get("interval", DEFAULT_INTERVAL))
    duration = float(cmd.get("duration", 0))           # Total duration in seconds

    # Calculate number of samples based on duration and interval
    if duration == 0:
        count = 1
    elif duration > 0:
        # Floor division ensures at least one sample
        count = int(duration // interval) or 1
    else:
        # Negative duration => unlimited
        count = None
    return cmd, action, interval, count

# -----------------------------------------------------------------------------
# Wi-Fi connection helper
# -----------------------------------------------------------------------------
async def connect_to_wifi(ssid, password):
    """
    Connect to Wi-Fi network using station interface.
    Retries until connection is successful.
    """
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()                # Reset any existing connection
    sta.active(False)
    await asyncio.sleep(1)
    sta.active(True)
    sta.connect(ssid, password)
    print('[TCP] Connecting to network...')
    # Wait until connected
    while not sta.isconnected():
        await asyncio.sleep(1)
    print('[TCP] Allocated IP:', sta.ifconfig()[0])

# -----------------------------------------------------------------------------
# TCP handler: read commands and send sensor data
# -----------------------------------------------------------------------------
async def handle_tcp(reader, writer):
    """
    Handle an open TCP connection:
      - Read lines (JSON commands) from reader
      - Parse and validate instruction
      - Loop to read sensor data and send JSON responses
      - Exit on 'exit' command
    """
    while True:
        try:
            # Wait up to 1s for a command line
            line = await asyncio.wait_for(reader.readline(), timeout=1)
        except asyncio.TimeoutError:
            await asyncio.sleep(0)
            continue
        if not line:
            await asyncio.sleep(0)
            continue

        print("[TCP] Received line:", line)
        try:
            cmd, action, interval, count = get_instruction(line)
        except Exception as e:
            # Send error if JSON invalid
            await writer.awrite(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            await writer.drain()
            await asyncio.sleep(0)
            continue

        if action == "exit":
            print("[TCP] Exiting...")
            return

        # Send 'count' readings at 'interval' spacing
        i = 0
        while True:
            resp = mpu6050_read(action)
            await writer.awrite(ujson.dumps(resp) + '\n')
            await writer.drain()
            i += 1
            if count is not None and i >= count:
                break
            await asyncio.sleep(interval)

        # Log completion of block
        print("---------------------------------------------------")
        print("\t\t[TCP] DATA UPLOADED!")
        print("---------------------------------------------------")

# -----------------------------------------------------------------------------
# TCP worker: ensure Wi-Fi and server connection
# -----------------------------------------------------------------------------
async def tcp_worker():
    """
    Continuously connect to Wi-Fi and then to the TCP server.
    On disconnection or error, retry indefinitely.
    """
    global SSID, PASSWORD, SERVER_IP, PORT
    connected_to_wifi = False
    # Retry Wi-Fi connection until successful
    while not connected_to_wifi:
        try:
            await asyncio.wait_for(connect_to_wifi(SSID, PASSWORD), timeout=10)
            connected_to_wifi = True
        except Exception as e:
            print("[TCP] Failed to connect to SSID: %s" % e)
            print("[TCP] Retrying...")
    # Main loop: connect to server and handle session
    while True:
        try:
            print("[TCP] Connecting to server IP: %s port: %s ..." % (SERVER_IP, PORT))
            try:
                reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
                await handle_tcp(reader, writer)
            except OSError as e:
                print("[TCP] Failed to connect to server: %s" % e)
                await asyncio.sleep(0)
                continue

            print("[TCP] Disconnecting from server...")
            reader.close()
            writer.close()
            await asyncio.sleep(0)
        except Exception as e:
            print("[TCP] Worker error:", e)
            await asyncio.sleep(0)
            continue

# -----------------------------------------------------------------------------
# UART worker: similar logic over serial port
# -----------------------------------------------------------------------------
async def uart_worker():
    """
    Continuously read JSON commands over UART,
    parse them, and send sensor data back over UART.
    Exit on 'exit' command or retry on errors.
    """
    while True:
        try:
            print('[Serial] UART connection open')
            while True:
                line = uart.readline()
                if not line:
                    await asyncio.sleep(0)
                    continue
                print("[Serial] Received line: %s" % line)
                try:
                    cmd, action, interval, count = get_instruction(line)
                except Exception as e:
                    uart.write(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
                    await asyncio.sleep(0)
                    continue

                if action == "exit":
                    print("[Serial] Exiting...")
                    return

                i = 0
                while True:
                    resp = mpu6050_read(action)
                    uart.write(ujson.dumps(resp) + "\n")
                    i += 1
                    if count is not None and i >= count:
                        break
                    await asyncio.sleep(interval)

                print("---------------------------------------------------")
                print("\t\t[Serial] DATA UPLOADED!")
                print("---------------------------------------------------")

        except Exception as e:
            print("[Serial] Worker error:", e)
            await asyncio.sleep(0)
            continue

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
async def main():
    # Create and run both TCP and UART workers concurrently
    tcp_task = asyncio.create_task(tcp_worker())
    uart_task = asyncio.create_task(uart_worker())
    await asyncio.gather(tcp_task, uart_task)

if __name__ == '__main__':
    # Run the main coroutine
    asyncio.run(main())
