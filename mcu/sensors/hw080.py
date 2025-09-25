from time import ticks_ms
from machine import ADC, Pin

# —— Configuration ——
# ADC input pin for the analog output (AO) of the HW080 sensor module
from .wiring import HW080_ADC_PIN
# Digital output pin (DO) from the internal comparator
from .wiring import HW080_DO_PIN
# Reference voltage for ADC conversion (in volts)
from .wiring import V_REF


class HW080:
    """
    Helper class for a typical HW080 soil moisture sensor module
    with both analog (AO) and digital (DO) outputs.
    """
    def __init__(
            self,
            adc_pin: int = HW080_ADC_PIN,
            do_pin: int = HW080_DO_PIN,
            v_ref: float = V_REF,
            pull_up: bool = False
    ):
        # Configure ADC pin
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.adc = ADC(Pin(adc_pin, *pin_kwargs))
        # Optionally adjust attenuation if supported
        try:
            self.adc.atten(ADC.ATTN_11DB)
        except AttributeError:
            pass

        # Configure digital output pin
        self.digital = Pin(do_pin, Pin.IN)
        self.v_ref = v_ref
        self.check_connection()

    def check_connection(self):
        try:
            _ = self.adc.read()
            _ = self.digital.value()
        except Exception as e:
            raise RuntimeError(f"HW080 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the HW080 sensor module.

        action:
          - "read_raw":     return raw ADC reading (0–4095)
          - "read_voltage": return measured AO voltage (volts)
          - "read_detected":return digital HW080 status (bool)
          - other or None:   return full report dict

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - raw:       ADC reading
            - voltage:   AO voltage (V)
            - detected:  soil moisture above threshold (True/False)
        """
        ts = ticks_ms()
        raw = self.adc.read()
        voltage = raw / 4095 * self.v_ref
        detected = bool(self.digital.value())

        report = {'timestamp': ts, 'sensor': "HW080"}
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_voltage':
            report['voltage'] = voltage
        elif action == 'read_detected':
            report['detected'] = detected
        else:
            report.update({
                'raw': raw,
                'voltage': voltage,
                'detected': detected
            })
        return report

# Usage example:
# hw080 = HW080()
# report = await hw080.do_read()                # Full report
# raw  = await hw080.do_read('read_raw')        # Only raw ADC
# volt = await hw080.do_read('read_voltage')    # Only voltage
# det  = await hw080.do_read('read_detected')   # Moisture detected status
