# led_main.py
import machine, time, ujson, sys
from machine import Pin
from MCUconfig import Config
config = Config()

LED_PIN = config.LED

led = Pin(LED_PIN, Pin.OUT)
time.sleep(2)

while True:
    line = sys.stdin.readline()
    if not line:
        continue
    try:
        cmd = ujson.loads(line)
        if cmd.get("command") == "led":
            state = cmd.get("state", "off").lower()
            led.value(1 if state == "on" else 0)
            resp = {"result": "ok", "state": state}
        else:
            resp = {"error": f"unknown command '{cmd.get('command')}'"}
    except Exception as e:
        resp = {"error": str(e)}
    sys.stdout.write(ujson.dumps(resp) + "\n")
