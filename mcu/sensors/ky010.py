from machine import Pin  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp

# —— Configuration ——
# Digital input pin for the KY-010 photo interrupter module
from .wiring import KY010_PIN


class KY010:
    """
    Driver class for a KY-010 photo interrupter (slot-type) module.

    Provides a digital signal indicating whether the light path is
    interrupted (blocked) or clear.
    """
    def __init__(
        self,
        pin_number: int = KY010_PIN,
        pull_up: bool = False
    ):
        """
        Initialize the photo interrupter on the given digital pin.

        Args:
          pin_number: GPIO pin connected to the module's OUT signal.
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
            raise RuntimeError(f"KY010 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read the sensor state.

        Args:
          action: (optional)
            - 'read_state':   return raw digital value (0 or 1)
            - 'is_blocked':   return boolean blocked status (True if interrupted)
            - other or None:  return full report

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - sensor:    sensor name
            - raw:       digital reading (0 or 1)
            - blocked:   boolean True if light path is interrupted
        """
        timestamp = ticks_ms()
        raw = self.pin.value()
        # On KY-010, raw==0 when IR beam is blocked, raw==1 when clear
        blocked = (raw == 0)

        report = {
            'timestamp': timestamp,
            'sensor':    'KY010',
        }
        if action == 'read_state':
            report['raw'] = raw
        elif action == 'is_blocked':
            report['blocked'] = blocked
        else:
            report.update({
                'raw': raw,
                'blocked': blocked
            })
        return report

# Example usage:
# sensor = KY010(pull_up=True)
# full = await sensor.do_read()             # {'timestamp':..., 'raw':1, 'blocked':False}
# state = await sensor.do_read('read_state')# {'timestamp':..., 'raw':1}
# blk = await sensor.do_read('is_blocked')  # {'timestamp':..., 'blocked':False}
