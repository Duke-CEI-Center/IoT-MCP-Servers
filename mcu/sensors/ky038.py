"""
Driver for the KY-038 / LM393 microphone-sound sensor module.

⚙️ 硬件要点
----------------------------------------------------------------------
• electret microphone + pre-amp + envelope rectifier  
• LM393 comparator → DO (digital HIGH/LOW)  
• potentiometer sets sound-level threshold  
• AO provides enveloped analog voltage proportional to loudness

参考资料：
  – SensorKit spec sheet  • sensorkit.joy-it.net/en/sensors/ky-038  [oai_citation:0‡sensorkit.joy-it.net](https://sensorkit.joy-it.net/en/sensors/ky-038?utm_source=chatgpt.com)
  – ESPBoards KY-038 overview • espboards.dev/sensors/ky-038/  [oai_citation:1‡espboards.dev](https://www.espboards.dev/sensors/ky-038/?utm_source=chatgpt.com)
"""

from collections import OrderedDict
from time import ticks_ms           # millisecond-precision timestamp
from machine import ADC, Pin         # MicroPython / ESP32 HAL

# —— Configuration ——
from .wiring import KY038_ADC_PIN    # Analog output (AO) pin
from .wiring import KY038_DO_PIN     # Digital output (DO) pin (LM393)
from .wiring import V_REF            # ADC reference voltage (V)

# If你的 ADC 是 12-bit（0-4095），保持默认；若 16-bit 改为 65535
_ADC_MAX = 4095


class KY038:
    """
    Helper class for the KY-038 sound sensor (analog + digital outputs).

    do_read(action):
      - 'read_raw'      ➜ 只返回 ADC 原始值 (0-4095)
      - 'read_voltage'  ➜ 只返回电压 (V)
      - 'read_trigger'  ➜ 只返回数字触发状态 (bool)
      - 其他 / 默认      ➜ 全量 OrderedDict
    """

    def __init__(
        self,
        adc_pin: int = KY038_ADC_PIN,
        do_pin: int = KY038_DO_PIN,
        v_ref: float = V_REF,
        pull_up: bool = False,
    ) -> None:
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)

        # ADC channel for AO
        self.adc = ADC(Pin(adc_pin))
        try:
            # 若是 ESP32，可设 0-3.3 V 量程
            self.adc.atten(ADC.ATTN_11DB)
        except AttributeError:
            pass  # 不支持衰减的 MCU 直接忽略

        # Digital output from LM393 comparator
        self.trigger = Pin(do_pin, *pin_kwargs)

        self.v_ref = v_ref
        self.check_connection()

    # ------------------------------------------------------------------
    # House-keeping
    # ------------------------------------------------------------------
    def check_connection(self) -> None:
        """Quick sanity-check that pins respond."""
        try:
            _ = self.adc.read()
            _ = self.trigger.value()
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError("KY-038 connection failure") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def do_read(self, action: str = ""):
        """
        Return OrderedDict with timestamp + requested fields.

        Fields:
            raw      – ADC integer
            voltage  – Converted voltage (V)
            level    – Normalised 0-1 loudness (optional helper)
            triggered – BOOL from LM393 comparator (sound > threshold)
        """
        ts = ticks_ms()
        raw = self.adc.read()
        voltage = raw / _ADC_MAX * self.v_ref
        triggered = bool(self.trigger.value())

        # Assemble response ------------------------------------------------
        report = OrderedDict([("timestamp", ts), ("sensor", "KY038")])

        if action == "read_raw":
            report["raw"] = raw
        elif action == "read_voltage":
            report["voltage"] = voltage
        elif action == "read_trigger":
            report["triggered"] = triggered
        else:  # full report
            report.update(
                {
                    "raw": raw,
                    "sensor": "ky038",
                    "voltage": voltage,
                    "level": voltage / self.v_ref,  # 0-1 loudness ratio
                    "triggered": triggered,
                }
            )
        return report


# -------------------------------
# Example usage (MicroPython REPL)
# -------------------------------
# from ky038 import KY038
# sound = KY038()
#
# import uasyncio as asyncio
#
# async def monitor():
#     while True:
#         print(await sound.do_read())           # Full report
#         await asyncio.sleep_ms(200)
#
# asyncio.run(monitor())