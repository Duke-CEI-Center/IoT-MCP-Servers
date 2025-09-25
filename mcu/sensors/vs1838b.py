from machine import Pin  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp

# —— Configuration ——
# Digital input pin for the VS1838B IR receiver module
from .wiring import VS1838B_PIN

class VS1838B:
    """
    Driver class for a VS1838B IR receiver module.

    The module demodulates incoming 38 kHz IR signals and outputs
    a digital pulse stream (active LOW when IR signal detected).
    """
    def __init__(
        self,
        pin_number: int = VS1838B_PIN,
        pull_up: bool = True
    ):
        """
        Initialize the IR receiver input pin.

        Args:
          pin_number: GPIO pin connected to the module's OUT.
          pull_up:    Whether to enable internal pull-up resistor (recommended).
        """
        # Configure digital input with pull-up to idle HIGH
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.pin = Pin(pin_number, *pin_kwargs)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Verify that the receiver pin is responsive.
        Raises RuntimeError on failure.
        """
        try:
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"VS1838B self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read the IR receiver digital output.

        Args:
          action: (optional)
            - 'read_raw':      return raw digital value (0 or 1)
            - 'is_detecting':  return boolean detection status (True if IR signal present)
            - other or None:   return full report

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - sensor:    sensor name
            - raw:       digital reading (0 or 1)
            - detecting: True if IR carrier detected (raw == 0)
        """
        ts = ticks_ms()
        raw = self.pin.value()
        # IR receiver outputs LOW when carrier pulses detected
        detecting = (raw == 0)

        report = {
            'timestamp': ts,
            'sensor':    'VS1838B',
        }
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'is_detecting':
            report['detecting'] = detecting
        else:
            report.update({
                'raw': raw,
                'detecting': detecting
            })
        return report

# Example usage:
# ir = VS1838B()
# full = await ir.do_read()               # Full report
# raw  = await ir.do_read('read_raw')     # Only raw digital value
# det  = await ir.do_read('is_detecting') # Only detection status
