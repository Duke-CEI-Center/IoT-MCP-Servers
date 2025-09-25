from time import ticks_ms
from machine import ADC, Pin

# —— Configuration ——
# ADC input pin for the analog output (AO) of the ky036 metal touch sensor module
from .wiring import KY036_ADC_PIN
# Digital output pin (DO) from the onboard comparator
from .wiring import KY036_DO_PIN
# Reference voltage for ADC conversion (in volts)
from .wiring import V_REF

class KY036:
    """
    Helper class for a typical metal-touch ky036 sensor module
    with both analog (AO) and digital (DO) outputs.
    """
    def __init__(
            self,
            adc_pin: int = KY036_ADC_PIN,
            do_pin: int = KY036_DO_PIN,
            v_ref: float = V_REF,
            pull_up: bool = False
    ):
        # Configure ADC pin for analog measurements
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.adc = ADC(Pin(adc_pin, *pin_kwargs))
        # Optionally adjust attenuation if supported
        try:
            self.adc.atten(ADC.ATTN_11DB)
        except AttributeError:
            pass

        # Configure digital output pin for touch detection
        self.digital = Pin(do_pin, Pin.IN)
        self.v_ref = v_ref
        self.check_connection()

    def check_connection(self):
        try:
            _ = self.adc.read()
            _ = self.digital.value()
        except Exception as e:
            raise RuntimeError(f"KY036 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the ky036 metal touch sensor module.

        action:
          - "read_raw":      return raw ADC reading (0–4095)
          - "read_voltage":  return measured AO voltage (volts)
          - "read_touched":  return digital sensing status (bool)
          - other or None:    return full report dict

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - raw:       ADC reading
            - voltage:   AO voltage (V)
            - touched:   touch status (True/False)
        """
        ts = ticks_ms()
        raw = self.adc.read()
        voltage = raw / 4095 * self.v_ref
        touched = bool(self.digital.value())

        report = {'timestamp': ts, 'sensor': "KY036"}
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_voltage':
            report['voltage'] = voltage
        elif action == 'read_touched':
            report['touched'] = touched
        else:
            report.update({
                'raw': raw,
                'voltage': voltage,
                'touched': touched
            })
        return report

# Usage example:
# ky036 = KY036()
# report = await ky036.do_read()                # Full report
# raw    = await ky036.do_read('read_raw')      # Only raw ADC
# volt   = await ky036.do_read('read_voltage')  # Only voltage
# touch  = await ky036.do_read('read_touched')  # Touch status
