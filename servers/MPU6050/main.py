import uasyncio as asyncio
from machine import Pin, SoftI2C, UART
from time import ticks_ms
from mpu6050 import MPU6050
import ujson, network, time, socket, sys

# Initialize the I2C bus, modify the parameter with the actual chip.
I2C = SoftI2C(scl=Pin(7), sda=Pin(6), freq=100000)

# Create an MPU6050 instance
MPU = MPU6050(I2C)

# Initialize uart, modify the parameter with the actual chip.
UART = UART(1, 115200, tx=17, rx=16)

DEFAULT_INTERVAL = 2

# Use config.py to modify the connection information.
SSID = "<SSID>"
PASSWORD = "<PASSWORD>"
SERVER_IP = "<SERVER_IP>"
PORT = "<PORT>"

#helper method: read data from sensor
def do_read(action):
    global MPU
    acc = MPU.read_accel_data()
    gyro = MPU.read_gyro_data()
    temp = MPU.read_temperature()
    angle = MPU.read_angle()
    if action == "read_temp":
        return {"timestamp": ticks_ms(), "temperature": temp}
    elif action == "read_accel":
        return {"timestamp": ticks_ms(), "accel": acc}
    elif action == "read_gyro":
        return {"timestamp": ticks_ms(), "gyro": gyro}
    elif action == "read_angle":
        return {"timestamp": ticks_ms(), "tilt": angle}
    else:
        return {
        "timestamp": ticks_ms(),
        "accel": acc,
        "gyro": gyro,
        "temperature": temp,
        "tilt": angle
    }

#helper method: decode instruction from server
def get_instruction(line):
    cmd = ujson.loads(line)
    action = cmd.get("command", "read_all")
    interval = float(cmd.get("interval", DEFAULT_INTERVAL))
    duration = float(cmd.get("duration", 0))
    if duration == 0:
        count = 1
    elif duration > 0:
        count = int(duration // interval) or 1
    else:
        count = None
    return cmd, action, interval, count

#helper method: connect to Wi-fi
async def connect_to_wifi(ssid, password):
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
    sta.active(False)
    await asyncio.sleep(1)
    sta.active(True)
    sta.connect(ssid, password)
    timeout = 0
    print('Connecting to network...')
    while not sta.isconnected():
        timeout += 1
        await asyncio.sleep(1)
        if timeout > 10:
            sta.disconnect()
            raise Exception('Network connection timed out')
    print('Allocated IP:', sta.ifconfig()[0])

#helper method: for wi-fi connection, decode the command and upload the monitored data
async def get_command_and_upload_data(reader, writer):
    while True:
        command = await reader.readline()
        if not command:
            await asyncio.sleep(0)
            continue
        try:
            cmd, action, interval, count = get_instruction(command)
            if action == "exit":
                print("Finish monitoring. Exiting...")
                return
        except Exception as e:
            await writer.awrite(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            continue

        i = 0
        while True:
            try:
                resp = do_read(action)
            except Exception as e:
                resp = {"error": str(e)}
            await writer.awrite(ujson.dumps(resp) + '\n')

            i += 1
            if count is not None and i >= count:
                break
            await asyncio.sleep(interval)

#main method that connect to server via Wi-fi
async def connect_to_server_via_wifi(server_ip, port):
    print("Connecting to server IP: %s port: %s ..." % (server_ip, port))
    connected_to_server = False
    time_out = 10
    while not connected_to_server:
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(server_ip, port), timeout=time_out)
            connected_to_server = True
            print("Connected to server!")
            await get_command_and_upload_data(reader, writer)
            reader.close()
            writer.close()
            await asyncio.sleep(1)
        except asyncio.TimeoutError:
            print("Connecting to server...")
            await asyncio.sleep(1)

#main method that connect to server via port
async def connect_to_server_via_port():
    print('Connecting to port...')
    while True:
        command = UART.readline()
        if not command:
            await asyncio.sleep(0)
            continue
        print("Connected to port! Received command: %s" % command)
        try:
            cmd, action, interval, count = get_instruction(command)
            if action == "exit":
                print("Finish monitoring. Exiting...")
                return
        except Exception as e:
            UART.write(ujson.dumps({"error": f"bad json: {e}"}) + "\n")
            await asyncio.sleep(1)
            continue

        i = 0
        while True:
            try:
                resp = do_read(action)
            except Exception as e:
                resp = {"error": str(e)}
            UART.write(ujson.dumps(resp) + "\n")
            i += 1
            if count is not None and i >= count:
                break
            await asyncio.sleep(interval)

async def wifi_worker():
    connected_to_wifi = False
    while not connected_to_wifi:
        try:
            await connect_to_wifi(SSID, PASSWORD)
            connected_to_wifi = True
        except Exception as e:
            print("Failed to connect to SSID: %s" % e)
            print("Retrying...")
    while True:
        try:
            # Run the Wi-Fi connection attempt (no return value needed)
            await connect_to_server_via_wifi(SERVER_IP, PORT)
            print("---------------------------------------------------")
            print(f"\t\tWi-Fi TASK COMPLETE!")
            print("---------------------------------------------------")
        except Exception as e:
            print("Wi-Fi worker error:", e)
            await asyncio.sleep(1)
            continue
    # Mark this worker as first if event not yet set

async def port_worker():
    while True:
        try:
            # Run the serial-port connection attempt
            await connect_to_server_via_port()
            print("---------------------------------------------------")
            print(f"\t\tPort TASK COMPLETE!")
            print("---------------------------------------------------")
        except Exception as e:
            print("Port worker error:", e)
            await asyncio.sleep(10)
            continue

async def main():
    wifi_task = asyncio.create_task(wifi_worker())
    port_task = asyncio.create_task(port_worker())
    await asyncio.gather(wifi_task, port_task)

if __name__ == '__main__':
    asyncio.run(main())

