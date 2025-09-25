from time import ticks_ms
from machine import ADC, Pin

# —— Configuration ——
# ADC input pin for the analog output (AO) of the KY‑037 sound sensor
from .wiring import KY037_ADC_PIN
# Digital output pin (DO) connected to the LM393 comparator
from .wiring import KY037_DO_PIN
# Reference voltage for ADC conversion (in volts)
from .wiring import V_REF


class KY037:
    """High‑sensitivity microphone (KY‑037) with analog (AO) + digital (DO) outputs."""

    def __init__(
        self,
        adc_pin: int = KY037_ADC_PIN,
        do_pin: int = KY037_DO_PIN,
        v_ref: float = V_REF,
        pull_up: bool = False,
    ):
        # Configure ADC channel (AO)
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.adc = ADC(Pin(adc_pin, *pin_kwargs))
        try:
            # On ESP32 enable full‑scale 0‑3.3 V range
            self.adc.atten(ADC.ATTN_11DB)  # type: ignore[attr-defined]
        except AttributeError:
            pass  # Not all MCUs support attenuation

        # Digital comparator output (DO)
        self.digital = Pin(do_pin, Pin.IN)
        self.v_ref = v_ref
        self.check_connection()

    # ------------------------------------------------------------------
    def check_connection(self) -> None:
        """Simple self‑test: ADC & digital pin must respond."""
        try:
            _ = self.adc.read()
            _ = self.digital.value()
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"KY037 self‑check failed: {exc}") from exc

    # ------------------------------------------------------------------
    async def do_read(self, action: str | None = None) -> dict:
        """Read sensor data.

        *action* 说明：
          • ``"read_raw"``      → 只返回 ADC 原始值 (0‑4095)
          • ``"read_voltage"``  → 只返回 AO 电压 (V)
          • ``"read_trigger"``  → 只返回数字触发状态 (bool)
          • ``None / 其他``       → 返回完整报告
        """
        ts = ticks_ms()
        raw = self.adc.read()
        voltage = raw / 4095 * self.v_ref  # 12‑bit ADC 默认量程
        triggered = bool(self.digital.value())

        report = {"timestamp": ts, "sensor": "KY037"}
        if action == "read_raw":
            report["raw"] = raw
        elif action == "read_voltage":
            report["voltage"] = voltage
        elif action == "read_trigger":
            report["triggered"] = triggered
        else:
            report.update({
                "raw": raw,
                "sensor": "ky037",
                "voltage": voltage,
                "triggered": triggered,
            })
        return report


# --------------------  Usage example (MicroPython REPL)  --------------------
# ky037 = KY037()
# full  = await ky037.do_read()                # 完整报告
# raw   = await ky037.do_read("read_raw")      # 仅原始 ADC
# volt  = await ky037.do_read("read_voltage")  # 仅电压 (V)
# trig  = await ky037.do_read("read_trigger")  # 仅数字触发
