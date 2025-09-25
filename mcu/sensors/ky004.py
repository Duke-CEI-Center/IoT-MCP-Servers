from machine import Pin  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp

# —— Configuration ——
# Digital input pin for the KY-004 button module
from .wiring import KY004_PIN


class KY004:
    """
    Driver class for a KY-004 push-button module.

    Provides a digital signal (0 or 1) indicating button state.
    """
    def __init__(
        self,
        pin_number: int = KY004_PIN,
        pull_up: bool = False
    ):
        """
        Initialize the button on the given digital pin.

        Args:
          pin_number: GPIO pin connected to the module's S output.
          pull_up:    Whether to enable internal pull-up resistor.
        """
        # Configure digital input pin, optionally with pull-up
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.pin = Pin(pin_number, *pin_kwargs)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Verify that the sensor pin is responsive.
        Raises RuntimeError on failure.
        """
        try:
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"KY004 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read the button state.

        Args:
          action: (optional)
            - 'read_state':   return raw digital value (0 or 1)
            - 'is_pressed':   return boolean pressed status (True if high)
            - other or None:  return full report

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - sensor:    sensor name
            - raw:       digital reading (0 or 1)
            - pressed:   boolean True if button is pressed
        """
        timestamp = ticks_ms()
        raw = self.pin.value()
        pressed = bool(raw)

        report = {
            'timestamp': timestamp,
            'sensor':    'KY004',
        }
        if action == 'read_state':
            report['raw'] = raw
        elif action == 'is_pressed':
            report['pressed'] = pressed
        else:
            report.update({
                'raw': raw,
                'pressed': pressed
            })
        return report

# Example usage:
# button = KY004()
# full = await button.do_read()          # {'timestamp':..., 'raw':0, 'pressed':False}
# state = await button.do_read('read_state')  # {'timestamp':..., 'raw':0}
# press = await button.do_read('is_pressed')  # {'timestamp':..., 'pressed':False}
