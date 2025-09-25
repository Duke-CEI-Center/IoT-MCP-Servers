from collections import OrderedDict
from time import ticks_ms
from machine import ADC, Pin

# —— Configuration ————————————————————————————————————————————————
from .wiring import UV_ADC_PIN  # Grove SIG -> ADC pin
from .wiring import V_REF       # ADC reference voltage (V)

# 12-bit ADC range
_ADC_MAX = 4095
# UVI empirical conversion coefficient (can be calibrated with measurements)
UVI_COEF = 13.3


class GUVA_S12SD:
    """Grove GUVA-S12SD UV sensor – analog output version."""

    def __init__(
        self,
        adc_pin: int = UV_ADC_PIN,
        v_ref: float = V_REF,
        pull_up: bool = False,
    ) -> None:
        # Configure ADC channel
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.adc = ADC(Pin(adc_pin, *pin_kwargs))
        try:
            # For ESP32, set attenuation for full 0-3.3 V range
            self.adc.atten(ADC.ATTN_11DB)  # type: ignore[attr-defined]
        except AttributeError:
            # If attenuation method is unavailable, ignore
            pass

        self.v_ref = v_ref
        self.check_connection()

    # ------------------------------------------------------------------
    def check_connection(self) -> None:
        """Quick self-check: ensure ADC pin is readable and returns a valid value."""
        try:
            _ = self.adc.read()
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"GUVA-S12SD self-check failed: {exc}") from exc

    # ------------------------------------------------------------------
    async def do_read(self, action: str | None = None):
        """Acquire measurement.

        Actions:
          • "read_raw"      -> return raw ADC value (0-4095)
          • "read_voltage"  -> return voltage (V)
          • "read_uvi"      -> return estimated UVI
          • None / other     -> return full report
        """
        ts = ticks_ms()
        raw = self.adc.read()
        voltage = raw / _ADC_MAX * self.v_ref
        uvi = voltage * UVI_COEF

        report = OrderedDict([("timestamp", ts), ("sensor", "GUVA-S12SD")])

        if action == "read_raw":
            report["raw"] = raw
        elif action == "read_voltage":
            report["voltage"] = voltage
        elif action == "read_uvi":
            report["uvi"] = uvi
        else:
            report.update({
                "raw": raw,
                "sensor": "uv_guva_s12sd",
                "voltage": voltage,
                "uvi": uvi,
            })
        return report

# ------------------ Usage (MicroPython REPL) ------------------
# uv = GUVA_S12SD()
# print(await uv.do_read())           # full report
# print(await uv.do_read('read_uvi')) # UVI only
