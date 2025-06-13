# server.py
from mcp.server.fastmcp import FastMCP
import serial, json, time
from ..Terminalconfig import Config

config = Config()

PORT     = config.PORT
BAUDRATE = config.BAUDRATE
TIMEOUT  = 1

mcp = FastMCP("BUZZER")

@mcp.tool()
def buzzer(duration: float, frequency: float = 1000.0) -> dict:
    """
    Activate the ESP32 buzzer.
    Args:
      duration: buzz time in seconds
      frequency: PWM frequency in Hz
    Returns:
      {"result":"ok","duration":<duration>,"frequency":<frequency>}
    """
    ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    time.sleep(2)

    cmd = {"command":"buzzer", "duration":duration, "frequency":frequency}
    ser.write((json.dumps(cmd) + "\n").encode())
    raw = ser.readline().decode().strip()
    ser.close()

    resp = json.loads(raw)
    if "error" in resp:
        raise RuntimeError(resp["error"])
    return resp

if __name__ == "__main__":
    mcp.serve(host="0.0.0.0", port=8000)
