import uasyncio as asyncio
from machine import Pin, SoftI2C, UART
from time import ticks_ms
import dht, ujson, network, time, socket, sys

# Initialize DHT11 sensor on pin 4 (modify as needed)
DHT_PIN = Pin(4, Pin.IN, Pin.PULL_UP)
sensor = dht.DHT11(DHT_PIN)

# Initialize UART, modify the parameters as needed
uart = UART(1, 115200, tx=17, rx=16)

DEFAULT_INTERVAL = 2

# Use config.py to modify the connection information.
SSID = "<SSID>"
PASSWORD = "<PASSWORD>"
SERVER_IP = "<SERVER_IP>"
PORT = "<PORT>" 

def do_read(action):
    """
    Read from DHT11 sensor and return JSONable dict
    supported actions: 'read_all', 'read_temp', 'read_hum'
    """
    timestamp = ticks_ms()
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
    except Exception as e:
        return {"timestamp": timestamp, "error": str(e)}

    if action == "read_temp":
        return {"timestamp": timestamp, "temperature": temp}
    elif action == "read_hum":
        return {"timestamp": timestamp, "humidity": hum}
    else:  # read_all or any other
        return {
            "timestamp": timestamp,
            "temperature": temp,
            "humidity": hum
        }

def get_instruction(line):
    """
    Decode incoming JSON command line
    Returns: cmd_dict, action, interval_secs, count
    """
    cmd = ujson.loads(line)
    action = cmd.get("command", "read_all")
    interval = float(cmd.get("interval", DEFAULT_INTERVAL))
    duration = float(cmd.get("duration", 0))

    if duration == 0:
        count = 1
    elif duration > 0:
        count = max(int(duration // interval), 1)
    else:
        count = None
    return cmd, action, interval, count

async def connect_to_wifi(ssid, password):
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
    sta.active(True)
    sta.connect(ssid, password)
    timeout = 0
    print("Connecting to Wi-Fi...")
    while not sta.isconnected():
        await asyncio.sleep(1)
        timeout += 1
        if timeout > 10:
            sta.disconnect()
            raise Exception("Wi-Fi connection timed out")
    print("Connected, IP:", sta.ifconfig()[0])

async def handle_tcp(reader, writer):
    while True:
        line = await reader.readline()
        if not line:
            await asyncio.sleep(0)
            continue
        try:
            cmd, action, interval, count = get_instruction(line)
            if action == "exit":
                print("Exit command received. Closing TCP handler.")
                return
        except Exception as e:
            await writer.awrite(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            continue

        i = 0
        while True:
            resp = do_read(action)
            await writer.awrite(ujson.dumps(resp) + "\n")
            i += 1
            if count is not None and i >= count:
                break
            await asyncio.sleep(interval)

async def tcp_worker():
    while True:
        try:
            print("Connecting to server %s:%s ..." % (SERVER_IP, PORT))
            reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
            print("TCP connection established.")
            await handle_tcp(reader, writer)
            writer.close()
            reader.close()
            await asyncio.sleep(1)
        except Exception as e:
            print("TCP worker error:", e)
            await asyncio.sleep(2)

async def uart_worker():
    while True:
        line = uart.readline()
        if not line:
            await asyncio.sleep(0)
            continue
        try:
            cmd, action, interval, count = get_instruction(line)
            if action == "exit":
                print("Exit command received. Closing UART handler.")
                return
        except Exception as e:
            uart.write(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            await asyncio.sleep(1)
            continue

        i = 0
        while True:
            resp = do_read(action)
            uart.write(ujson.dumps(resp) + "\n")
            i += 1
            if count is not None and i >= count:
                break
            await asyncio.sleep(interval)

async def main():
    await connect_to_wifi(SSID, PASSWORD)
    tcp_task = asyncio.create_task(tcp_worker())
    uart_task = asyncio.create_task(uart_worker())
    await asyncio.gather(tcp_task, uart_task)

if __name__ == "__main__":
    asyncio.run(main())
