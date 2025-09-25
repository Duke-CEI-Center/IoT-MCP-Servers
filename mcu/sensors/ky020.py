from time import ticks_ms  # Millisecond timestamp
from machine import Pin  # Hardware interfaces

# —— Configuration ——
# Digital input pin for the KY-020 tilt switch module
from .wiring import KY020_PIN

class KY020:
    """
    Helper class for the KY-020 tilt switch module.
    Detects tilt by reading a digital input with an internal pull-up.
    """
    def __init__(
            self,
            pin_number: int = KY020_PIN,
            pull_up: bool = True
    ):
        # Configure digital input pin (enable internal pull-up by default)
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.pin = Pin(pin_number, *pin_kwargs)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Raise RuntimeError if the pin does not respond.
        """
        try:
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"KY020 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the KY-020 tilt switch module.

        action:
          - "read_raw":    return raw digital reading (0 or 1)
          - "read_tilted": return boolean tilted state (True if tilted)
          - other or None:  return full report with both fields

        Returns:
          dict containing:
            - timestamp: ms ticks
            - sensor:    "KY020"
            - raw:       digital value read (0/1)
            - tilted:    boolean True if switch is closed (tilted)
        """
        ts = ticks_ms()
        raw = self.pin.value()
        # In KY-020, pin is pulled HIGH normally; closes to GND when tilted
        tilted = (raw == 0)

        report = {"timestamp": ts, "sensor": "KY020"}
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_tilted':
            report['tilted'] = tilted
        else:
            report.update({'raw': raw, 'tilted': tilted})
        return report
