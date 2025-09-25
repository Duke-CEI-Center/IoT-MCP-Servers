from time import ticks_ms  # Millisecond timestamp
from machine import Pin  # Hardware interfaces

# —— Configuration ——
# Digital input pin for the TTP223 capacitive touch sensor module
from .wiring import TTP223_PIN

class TTP223:
    """
    Helper class for the TTP223 capacitive touch sensor module.
    Detects touch by reading a digital input with an optional internal pull-down.
    """
    def __init__(
            self,
            pin_number: int = TTP223_PIN,
            pull_up: bool = False
    ):
        # Configure digital input pin (enable internal pull-down by default)
        if pull_up:
            pin_kwargs = (Pin.IN, Pin.PULL_UP)
        else:
            pin_kwargs = (Pin.IN, Pin.PULL_DOWN)
        self.pin = Pin(pin_number, *pin_kwargs)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Raise RuntimeError if the pin does not respond.
        """
        try:
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"TTP223 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the TTP223 capacitive touch sensor module.

        action:
          - "read_raw":    return raw digital reading (0 or 1)
          - "read_touched":return boolean touch state (True if touched)
          - other or None:  return full report with both fields

        Returns:
          dict containing:
            - timestamp: ms ticks
            - sensor:    "TTP223"
            - raw:       digital value read (0/1)
            - touched:   boolean True if sensor is triggered (touched)
        """
        ts = ticks_ms()
        raw = self.pin.value()
        # In TTP223 default mode, pin is LOW normally; goes HIGH when touched
        touched = (raw == 1)

        report = {"timestamp": ts, "sensor": "TTP223"}
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_touched':
            report['touched'] = touched
        else:
            report.update({'raw': raw, 'touched': touched})
        return report