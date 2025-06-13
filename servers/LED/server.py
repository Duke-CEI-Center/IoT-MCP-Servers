# server.py
from mcp.server.fastmcp import FastMCP
import serial, json, time
from ..Terminalconfig import Config

config = Config()

PORT     = config.PORT
BAUDRATE = config.BAUDRATE

TIMEOUT  = 1  

mcp = FastMCP("LED")

@mcp.tool()
def led(state: str) -> dict:
    """
    Turn the ESP32 LED on or off.
    Args:
      state: "on" or "off"
    Returns:
      {"result":"ok","state":<state>}
    """
    ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    time.sleep(2)  # wait for ESP32 to reboot/run led_main.py

    cmd = {"command": "led", "state": state}
    ser.write((json.dumps(cmd) + "\n").encode())
    raw = ser.readline().decode().strip()
    ser.close()

    resp = json.loads(raw)
    if "error" in resp:
        raise RuntimeError(resp["error"])
    return resp

if __name__ == "__main__":
    mcp.serve(host="0.0.0.0", port=8000)
