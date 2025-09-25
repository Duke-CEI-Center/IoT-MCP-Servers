# ky023.py
from machine import ADC, Pin
from time import ticks_ms

# —— Configuration ——
# ADC pins and digital pin for KY-023 joystick module
from .wiring import (
    KY023_ADC_X_PIN,
    KY023_ADC_Y_PIN,
    KY023_SW_PIN,
    ADC_ATTENUATION,
    V_REF
)


class KY023:
    """
    Driver for KY-023 2-axis joystick module with push-button.
    Provides analog readings for X and Y axes, and digital reading for button.
    """
    def __init__(
        self,
        adc_x_pin: int   = KY023_ADC_X_PIN,
        adc_y_pin: int   = KY023_ADC_Y_PIN,
        sw_pin: int      = KY023_SW_PIN,
        v_ref: float     = V_REF,
        pull_up: bool    = False
    ):
        """
        Initialize ADC and digital input pins.

        Args:
          adc_x_pin: GPIO pin for X-axis ADC
          adc_y_pin: GPIO pin for Y-axis ADC
          sw_pin:    GPIO pin for joystick button
          v_ref:     reference voltage for ADC conversion
          pull_up:   enable internal pull-up for SW if True
        """
        # ADC for X and Y
        self.adc_x = ADC(Pin(adc_x_pin))
        self.adc_y = ADC(Pin(adc_y_pin))
        # Set attenuation if supported
        try:
            self.adc_x.atten(ADC_ATTENUATION)
            self.adc_y.atten(ADC_ATTENUATION)
        except AttributeError:
            pass

        # Digital input for switch
        mode = Pin.IN_PULL if pull_up else Pin.IN
        self.sw = Pin(sw_pin, mode)
        self.v_ref = v_ref
        self.check_connection()

    def check_connection(self) -> None:
        """
        Verify ADC and switch respond.
        Raises RuntimeError on failure.
        """
        try:
            _ = self.adc_x.read()
            _ = self.adc_y.read()
            _ = self.sw.value()
        except Exception as e:
            raise RuntimeError(f"KY023 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from joystick module.

        action options:
          - 'read_x':      return X-axis voltage only
          - 'read_y':      return Y-axis voltage only
          - 'read_raw':    return raw ADC readings for both axes
          - 'read_switch': return button pressed state
          - other or None: return full report

        Returns dict with keys:
          - timestamp: current ticks_ms()
          - sensor:    'KY023'
          - raw:       dict(x: raw_x, y: raw_y)
          - voltage:   dict(x: volt_x, y: volt_y)
          - pressed:   bool (True if button pressed)
        """
        ts = ticks_ms()
        raw_x = self.adc_x.read()
        raw_y = self.adc_y.read()
        # ADC range assumed 0-4095
        volt_x = raw_x / 4095 * self.v_ref
        volt_y = raw_y / 4095 * self.v_ref
        pressed = self.sw.value() == 0

        report = {'timestamp': ts, 'sensor': 'KY023'}
        if action == 'read_x':
            report['voltage'] = volt_x
        elif action == 'read_y':
            report['voltage'] = volt_y
        elif action == 'read_raw':
            report['raw'] = {'x': raw_x, 'y': raw_y}
        elif action == 'read_switch':
            report['pressed'] = pressed
        else:
            report.update({
                'raw': {'x': raw_x, 'y': raw_y},
                'voltage': {'x': volt_x, 'y': volt_y},
                'pressed': pressed
            })
        return report

# Example usage:
# from ky_modules import ky023
# joystick = KY023(pull_up=True)
# state_all = await joystick.do_read()
# x = await joystick.do_read('read_x')
# y = await joystick.do_read('read_y')
# raw = await joystick.do_read('read_raw')
# btn = await joystick.do_read('read_switch')
