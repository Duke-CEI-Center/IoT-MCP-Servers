from machine import Pin  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp

# —— Configuration ——
# Digital input pins for the KY-040 rotary encoder module
from .wiring import KY040_CLK_PIN, KY040_DT_PIN, KY040_SW_PIN


class KY040:
    """
    Driver class for a KY-040 incremental rotary encoder module with push-button.

    Provides two digital signals (CLK/A and DT/B) for rotation detection,
    and one digital signal (SW) for the integrated push-button switch.
    """
    def __init__(
        self,
        clk_pin: int = KY040_CLK_PIN,
        dt_pin: int = KY040_DT_PIN,
        sw_pin: int = KY040_SW_PIN,
        pull_up: bool = False,
    ):
        """
        Initialize the rotary encoder pins.

        Args:
          clk_pin: GPIO pin connected to encoder channel A (CLK).
          dt_pin:  GPIO pin connected to encoder channel B (DT).
          sw_pin:  GPIO pin connected to encoder push-button (SW).
          pull_up: enable internal pull-up resistor if True.
        """
        # Configure digital input pins
        pin_cfg = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.clk = Pin(clk_pin, *pin_cfg)
        self.dt = Pin(dt_pin, *pin_cfg)
        self.sw = Pin(sw_pin, *pin_cfg)
        self.check_connection()

    def check_connection(self) -> None:
        """
        Quick sanity-check to verify encoder pins respond.
        Raises RuntimeError if any pin read fails.
        """
        try:
            _ = self.clk.value()
            _ = self.dt.value()
            _ = self.sw.value()
        except Exception as e:
            raise RuntimeError(f"KY040 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read current state of the rotary encoder signals.

        Args:
          action: (optional)
            - 'read_clk':    return only CLK/A pin value
            - 'read_dt':     return only DT/B pin value
            - 'read_switch': return only raw SW value (0 or 1)
            - 'is_pressed':  return boolean push-button state (True if pressed)
            - other or None: return full report

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - sensor:    sensor name 'KY040'
            - clk:       digital reading of CLK/A (0 or 1)
            - dt:        digital reading of DT/B (0 or 1)
            - switch:    raw digital reading of SW (0 or 1)
            - pressed:   boolean True if SW is pressed (raw value == 0)
        """
        ts = ticks_ms()
        raw_clk = self.clk.value()
        raw_dt = self.dt.value()
        raw_sw = self.sw.value()
        # Many modules pull SW to ground when pressed
        pressed = raw_sw == 0

        report = {
            'timestamp': ts,
            'sensor':    'KY040',
        }
        if action == 'read_clk':
            report['clk'] = raw_clk
        elif action == 'read_dt':
            report['dt'] = raw_dt
        elif action == 'read_switch':
            report['switch'] = raw_sw
        elif action == 'is_pressed':
            report['pressed'] = pressed
        else:
            report.update({
                'clk':     raw_clk,
                'dt':      raw_dt,
                'switch':  raw_sw,
                'pressed': pressed,
            })
        return report

# Example usage:
# encoder = KY040(pull_up=True)
# state = await encoder.do_read()           # Full report
# a = await encoder.do_read('read_clk')     # Only CLK
# b = await encoder.do_read('read_dt')      # Only DT
# sw = await encoder.do_read('read_switch') # Only switch raw
# btn = await encoder.do_read('is_pressed') # Button press state
