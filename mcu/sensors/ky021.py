from time import ticks_ms  # Millisecond timestamp
from machine import Pin, ADC  # Hardware interfaces

# —— Configuration ——
# Digital input pin for the KY-021 tilt switch module
to_pin_config = ['KY021_DO_PIN', 'KY021_AO_PIN']  # Ensure wiring module defines both
from .wiring import KY021_DO_PIN, KY021_AO_PIN


class KY021:
    """
    Driver class for a KY-021 tilt sensor module with both digital (DO) and analog (AO) outputs.

    The module provides:
      - DO: a digital output that goes HIGH when tilted beyond the activation angle.
      - AO: an analog output that varies with the tilt angle (as a resistance-based potentiometer).
    """
    def __init__(
        self,
        do_pin: int = KY021_DO_PIN,
        ao_pin: int = KY021_AO_PIN,
        pull_up: bool = False
    ):
        # Initialize the digital input pin (DO), optionally with pull-up resistor
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.do = Pin(do_pin, *pin_kwargs)
        # Initialize the analog input pin (AO)
        self.ao = ADC(Pin(ao_pin))
        self.check_connection()

    def check_connection(self) -> None:
        """
        Raise RuntimeError if the sensor pins are not responsive.
        """
        try:
            _ = self.do.value()
            _ = self.ao.read()  # or read_u16 on some platforms
        except Exception as e:
            raise RuntimeError(f"KY021 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the KY-021 tilt sensor.

        action options:
          - "read_do":    return raw digital value (0 or 1)
          - "read_ao":    return raw analog value (e.g., 0–1023 or 0–65535)
          - "is_tilted":  return tilt status as boolean
          - other or None: return full report with timestamp, digital, analog, and tilted

        Returns:
            dict containing:
              - timestamp: current ticks_ms()
              - digital:   digital reading (0 or 1)
              - analog:    analog reading as integer
              - tilted:    True if tilt switch closed (digital HIGH)
        """
        ts = ticks_ms()
        raw_do = self.do.value()
        try:
            raw_ao = self.ao.read()
        except AttributeError:
            # some ports use read_u16()
            raw_ao = self.ao.read_u16()
        tilted = bool(raw_do)

        report = {"timestamp": ts, "sensor": "KY021"}
        if action == 'read_do':
            report['digital'] = raw_do
        elif action == 'read_ao':
            report['analog'] = raw_ao
        elif action == 'is_tilted':
            report['tilted'] = tilted
        else:
            report.update({
                'digital': raw_do,
                'analog': raw_ao,
                'tilted': tilted
            })
        return report


# Example usage:
# sensor = KY021()
# full = await sensor.do_read()          # {'timestamp':..., 'digital':1, 'analog':512, 'tilted':True}
# d = await sensor.do_read('read_do')    # {'timestamp':..., 'digital':1}
# a = await sensor.do_read('read_ao')    # {'timestamp':..., 'analog':512}
# t = await sensor.do_read('is_tilted')  # {'timestamp':..., 'tilted':True}
