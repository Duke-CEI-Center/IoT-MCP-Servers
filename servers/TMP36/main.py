import uasyncio as asyncio
from machine import Pin, ADC, UART
from time import ticks_ms
import ujson, network, time, sys

# Initialize TMP36 on ADC pin 34 (modify as needed)
adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)       # full voltage range: 0–3.3V
adc.width(ADC.WIDTH_12BIT)    # 12-bit resolution

# Initialize UART (modify TX/RX pins if necessary)
uart = UART(1, 115200, tx=17, rx=16)

DEFAULT_INTERVAL = 2

# Use config.py to modify these
SSID       = "<SSID>"
PASSWORD   = "<PASSWORD>"
SERVER_IP  = "<SERVER_IP>"
PORT       = "<PORT>" 

def read_temperature():
    """
    Read raw ADC from TMP36, convert to °C.
    """
    raw = adc.read()
    voltage = raw / 4095 * 3.3           # volts
    temp_c = (voltage - 0.5) * 100       # TMP36: 10mV/°C with 500mV offset
    return temp_c

def do_read(action):
    """
    Supported actions: 'read_temp', 'read_all'
    """
    timestamp = ticks_ms()
    try:
        temp = read_temperature()
    except Exception as e:
        return {"timestamp": timestamp, "error": str(e)}

    if action in ("read_temp", "read_all"):
        return {"timestamp": timestamp, "temperature": temp}
    else:
        return {"timestamp": timestamp, "error": "unknown command"}

def get_instruction(line):
    """
    Parse incoming JSON line.
    Returns: cmd_dict, action, interval (s), count
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
                print("Exit command received; closing TCP handler.")
                return
        except Exception as e:
            await writer.awrite(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            continue

        sent = 0
        while True:
            resp = do_read(action)
            await writer.awrite(ujson.dumps(resp) + "\n")
            sent += 1
            if count is not None and sent >= count:
                break
            await asyncio.sleep(interval)

async def tcp_worker():
    while True:
        try:
            print(f"Connecting to {SERVER_IP}:{PORT}...")
            reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
            print("TCP connected.")
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
                print("Exit command received; closing UART handler.")
                return
        except Exception as e:
            uart.write(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            await asyncio.sleep(1)
            continue

        sent = 0
        while True:
            resp = do_read(action)
            uart.write(ujson.dumps(resp) + "\n")
            sent += 1
            if count is not None and sent >= count:
                break
            await asyncio.sleep(interval)

async def main():
    await connect_to_wifi(SSID, PASSWORD)
    tcp_task = asyncio.create_task(tcp_worker())
    uart_task = asyncio.create_task(uart_worker())
    await asyncio.gather(tcp_task, uart_task)

if __name__ == "__main__":
    asyncio.run(main())
