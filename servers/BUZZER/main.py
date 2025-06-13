# buzzer_main.py
import machine, time, ujson, sys
from machine import Pin, PWM
from MCUconfig import Config
config = Config()
BUZZER_PIN = config.BUZZER

buzzer = PWM(Pin(BUZZER_PIN), freq=1000, duty=0)
time.sleep(2)

while True:
    line = sys.stdin.readline()
    if not line:
        continue
    try:
        cmd = ujson.loads(line)
        if cmd.get("command") == "buzzer":
            duration  = float(cmd.get("duration", 1))
            frequency = int(cmd.get("frequency", 1000))
            buzzer.freq(frequency)
            buzzer.duty(512)
            time.sleep(duration)
            buzzer.duty(0)
            resp = {"result": "ok", "duration": duration, "frequency": frequency}
        else:
            resp = {"error": f"unknown command '{cmd.get('command')}'"}
    except Exception as e:
        resp = {"error": str(e)}
    sys.stdout.write(ujson.dumps(resp) + "\n")
