from collections import OrderedDict
from time import ticks_ms
from machine import Pin

# —— Configuration ——
from .wiring import WATER_SENSOR_PIN

class WaterSensor:
    """
    Driver class for a simple water level detection module (S+/– interface).

    Reads digital output: low/high indicates presence of water at probe level.
    """
    def __init__(
        self,
        pin_number: int = WATER_SENSOR_PIN,
        pull_up: bool = True,
        invert: bool = True
    ):
        """
        Initialize the water sensor input pin.

        Args:
          pin_number: GPIO pin connected to 'S' 引脚
          pull_up: whether to enable internal pull-up resistor
          invert: whether to invert digital reading (module active LOW)
        """
        self.invert = invert
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.pin = Pin(pin_number, *pin_kwargs)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Basic sanity check: read pin state, raise RuntimeError on failure.
        """
        try:
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"WaterSensor init failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read water presence at probe.

        Args:
          action: (optional)
            - 'read_raw': return raw pin value
            - 'read_bool': return interpreted boolean wet/dry
            - other or None: return full report

        Returns:
          OrderedDict containing:
            - timestamp: ms ticks
            - sensor:    'WaterSensor'
            - raw:       raw digital value (0 or 1)
            - wet:       True if water present, False otherwise
        """
        timestamp = ticks_ms()
        raw = self.pin.value()
        # Interpret wet/dry: if invert, raw=0 means wet
        wet = (not raw) if self.invert else bool(raw)

        report = OrderedDict([
            ("timestamp", timestamp),
            ("sensor", "WaterSensor"),
        ])
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_bool':
            report['wet'] = wet
        else:
            report.update({'raw': raw, 'wet': wet})
        return report

# Example usage:
# sensor = WaterSensor()
# r = await sensor.do_read('read_raw')   # {'timestamp':..., 'raw': 0}
# w = await sensor.do_read('read_bool')  # {'timestamp':..., 'wet': True}
# f = await sensor.do_read()             # {'timestamp':..., 'raw': 0, 'wet': True}
