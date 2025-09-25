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

def temp36_read(action):
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

# helper method: connect to Wi-fi
async def connect_to_wifi(ssid, password):
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
    sta.active(False)
    await asyncio.sleep(1)
    sta.active(True)
    sta.connect(ssid, password)
    print('[TCP] Connecting to network...')
    while not sta.isconnected():
        await asyncio.sleep(1)
    print('[TCP] Allocated IP:', sta.ifconfig()[0])

# helper method: for wi-fi connection, handle the read and write process
async def handle_tcp(reader, writer):
    while True:
        try:
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
            await writer.awrite(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            await writer.drain()
            await asyncio.sleep(0)
            continue

        if action == "exit":
            print("[TCP] Exiting...")
            return

        i = 0
        while True:
            resp = temp36_read(action)
            await writer.awrite(ujson.dumps(resp) + '\n')
            await writer.drain()
            i += 1
            if count is not None and i >= count:
                break
            await asyncio.sleep(interval)

        print("---------------------------------------------------")
        print(f"\t\t[TCP] DATA UPLOADED!")
        print("---------------------------------------------------")

# main method that connect to server via Wi-fi
async def tcp_worker():
    global SSID, PASSWORD, SERVER_IP, PORT
    connected_to_wifi = False
    while not connected_to_wifi:
        try:
            await asyncio.wait_for(connect_to_wifi(SSID, PASSWORD), timeout=10)
            connected_to_wifi = True
        except Exception as e:
            print("[TCP] Failed to connect to SSID: %s" % e)
            print("[TCP] Retrying...")
    while True:
        try:
            # Run the Wi-Fi connection attempt
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

# main method that connect to server via uart
async def uart_worker():
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
                    resp = temp36_read(action)
                    uart.write(ujson.dumps(resp) + "\n")
                    i += 1
                    if count is not None and i >= count:
                        break
                    await asyncio.sleep(interval)

                print("---------------------------------------------------")
                print(f"\t\t[Serial] DATA UPLOADED!")
                print("---------------------------------------------------")

        except Exception as e:
            print("[Serial] Worker error:", e)
            await asyncio.sleep(0)
            continue

async def main():
    tcp_worker_task = asyncio.create_task(tcp_worker())
    uart_worker_task = asyncio.create_task(uart_worker())
    await asyncio.gather(tcp_worker_task, uart_worker_task)


if __name__ == "__main__":
    asyncio.run(main())
