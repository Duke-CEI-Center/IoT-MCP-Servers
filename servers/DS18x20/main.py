import onewire, ds18x20
import uasyncio as asyncio  # Asynchronous IO library for microcontrollers
from machine import Pin, SoftI2C, UART  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp
import ujson, network  # JSON handling and network interface

# Initialize the 1-Wire bus on GPIO3 for DS18B20 temperature sensing
ow = onewire.OneWire(Pin(3))
# Create a DS18B20 instance
ds = ds18x20.DS18X20(ow)
# Scan the 1-Wire bus for all sensors ROM codes
roms = ds.scan()

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
def ds18x20_read(action):
    """
    Read data from one or more DS18B20 sensors based on action:
      - read_temp:       return temperatures for all sensors
      - read_rom:        return list of sensor ROM codes
      - read_scratchpad: return raw scratchpad bytes for each sensor
      - read_config:     return configuration register for each sensor
      - any other:       return a full report of all above
    Returns a dict with:
      - timestamp: current ticks_ms()
      - requested fields (temperatures, roms, scratchpads, configs)
      - or error on failure
    """
    global ds, roms
    ts = ticks_ms()
    try:
        # Trigger temperature conversion on all devices
        ds.convert_temp()
        # Wait max conversion time for 12-bit resolution if needed
        # time.sleep_ms(750)

        # Read temperatures
        temperatures = {rom: ds.read_temp(rom) for rom in roms}

    except Exception as e:
        return {"timestamp": ts, "error": str(e)}

    # Handle each action
    if action == "read_temp":
        return {"timestamp": ts, "temperatures": temperatures}

    elif action == "read_rom":
        return {"timestamp": ts, "roms": roms}

    elif action == "read_scratchpad":
        # read raw 9-byte scratchpad for each sensor
        scratchpads = {rom: ds.read_scratch(rom) for rom in roms}
        return {"timestamp": ts, "scratchpads": scratchpads}

    elif action == "read_config":
        # extract configuration byte (byte index 4) from scratchpad
        configs = {}
        for rom in roms:
            sp = ds.read_scratch(rom)
            configs[rom] = sp[4]
        return {"timestamp": ts, "configs": configs}

    else:
        # Default: full report
        scratchpads = {rom: ds.read_scratch(rom) for rom in roms}
        configs = {rom: scratchpads[rom][4] for rom in roms}
        return {
            "timestamp":     ts,
            "roms":          roms,
            "temperatures":  temperatures,
            "scratchpads":   scratchpads,
            "configs":       configs
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
            resp = ds18x20_read(action)
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
                    resp = ds18x20_read(action)
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
