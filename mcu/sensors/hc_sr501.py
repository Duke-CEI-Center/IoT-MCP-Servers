from machine import Pin  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp

# —— Configuration ——
# Digital output pin for the HC-SR501 PIR motion sensor
from .wiring import HC_SR501_PIN


class HC_SR501:
    """
    Driver class for an HC-SR501 PIR motion sensor module.
    """
    def __init__(
            self,
            pin_number: int = HC_SR501_PIN,
            pull_up: bool = False
    ):
        """
        Initialize the PIR motion sensor on the given digital pin.

        Args:
          pin_number: GPIO pin connected to the sensor's OUT.
          pull_up:    Whether to enable internal pull-up resistor.
        """
        # Configure digital input pin
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.pin = Pin(pin_number, *pin_kwargs)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Verify that the sensor responds on its output pin.
        Raises RuntimeError if not.
        """
        try:
            # Read pin state once
            _ = self.pin.value()
        except Exception as e:
            raise RuntimeError(f"HC-SR501 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read the PIR sensor output.

        Args:
          action: (optional)
            - 'read_motion': return motion detected state only
            - other or None: return full report

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - sensor:    sensor name
            - motion:    boolean, True if motion detected
        """
        timestamp = ticks_ms()
        # Read digital output: High when motion detected
        motion = bool(self.pin.value())

        report = {
            'timestamp': timestamp,
            'sensor':    'HC-SR501',
        }
        if action == 'read_motion':
            report['motion'] = motion
        else:
            # Full report
            report.update({
                'motion': motion
            })
        return report

# Usage example:
# pir = HC_SR501()
# report = await pir.do_read()            # Full report
# motion = await pir.do_read('read_motion')  # Only motion state
