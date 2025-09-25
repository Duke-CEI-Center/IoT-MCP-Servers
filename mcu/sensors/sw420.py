# sw420.py

from time import ticks_ms   # Millisecond timestamp
from machine import Pin      # Hardware interfaces

# —— Configuration ——
# Digital input pin for the SW-420 shock (vibration) switch module
from .wiring import SW420_PIN

class SW420:
    """
    Helper class for the SW-420 shock/vibration switch module.
    Detects shock by reading a digital input with an internal pull-down.
    """
    def __init__(
            self,
            pin_number: int = SW420_PIN,
            pull_down: bool = True
    ):
        # Configure digital input pin (enable internal pull-down by default)
        pin_kwargs = (Pin.IN, Pin.PULL_DOWN) if pull_down else (Pin.IN,)
        self.pin = Pin(pin_number, *pin_kwargs)
        self._self_test()

    def _self_test(self) -> None:
        """
        Raise RuntimeError if the pin does not respond.
        """
        try:
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"SW420 self-test failed: {e}")

    async def do_read(self, mode: str = None) -> dict:
        """
        Read data from the SW-420 shock/vibration switch module.

        mode:
          - "raw":     return raw digital reading (0 or 1)
          - "shock":   return boolean shock state (True if shock detected)
          - other or None: return full report with both fields

        Returns:
          {
            "timestamp": <ms ticks>,
            "sensor":    "SW420",
            "raw":       <0 or 1>,
            "shock":     <bool>
          }
        """
        ts = ticks_ms()
        raw_val = self.pin.value()
        # On SW-420, the pin stays LOW normally; goes HIGH when vibration/shock closes contact
        shock_detected = str(int(raw_val == 1))

        report = {
            "timestamp": ts,
            "sensor":    "SW420"
        }

        if mode == "raw":
            report["raw"] = raw_val
        elif mode == "shock":
            report["shock"] = shock_detected
        else:
            report.update({
                "raw":   raw_val,
                "shock": shock_detected
            })

        return report
