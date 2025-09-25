from time import ticks_ms  # Millisecond timestamp
from machine import ADC, Pin  # Hardware interfaces

# —— Configuration ——
# ADC input pin for the analog output (AO) of the KY035 module
from .wiring import KY035_ADC_PIN
# Digital output pin (DO) from the LM393 comparator
from .wiring import KY035_DO_PIN
# Reference voltage for ADC conversion (in volts)
from .wiring import V_REF

# Sensor sensitivity (volts per gauss).
# E.g., 3 mV/G ⇒ 0.003 V/G. Adjust to your module’s spec.
SENSITIVITY = 0.003


# -----------------------------------------------------------------------------
# Sensor read helper
# -----------------------------------------------------------------------------
class KY035:
    def __init__(
            self,
            adc_pin: int = KY035_ADC_PIN,
            do_pin: int = KY035_DO_PIN,
            sensitivity: float = SENSITIVITY,
            v_ref: float = V_REF,
            pull_up: bool = False
    ):
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.adc = ADC(Pin(adc_pin, *pin_kwargs))
        self.adc.atten(ADC.ATTN_11DB)
        self.switch = Pin(do_pin, Pin.IN)
        self.sensitivity = sensitivity
        self.v_ref = v_ref
        self.check_connection()

    def check_connection(self):
        try:
            _ = self.adc.read()
            _ = self.switch.value()
        except Exception as e:
            raise RuntimeError(f"KY035 self-check failed: {e}")


    async def do_read(self, action: str = None) -> dict:
        """
        Read data from a linear KY035 sensor module (with AO + DO).

        Arguments:
          action (str, optional):
            - "read_raw":     return raw ADC reading (0–4095)
            - "read_voltage": return measured AO voltage (volts)
            - "read_field":   return estimated magnetic field (gauss)
            - "read_switch":  return digital threshold status (bool)
            - other or None:  return full report dict

        Returns:
          dict containing:
            - timestamp: current ticks_ms()
            - raw:       ADC reading
            - voltage:   AO voltage (V)
            - field:     magnetic field strength (G)
            - switch:    threshold switch state (True if magnet detected)
        """
        ts = ticks_ms()
        raw = self.adc.read()
        voltage = raw / 4095 * self.v_ref

        # Compute magnetic field strength in gauss
        field = voltage / self.sensitivity

        # Read the comparator output: True if above threshold
        switch = bool(self.switch.value())

        report = {'timestamp': ts, "sensor": "KY035"}

        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_voltage':
            report['voltage'] = voltage
        elif action == 'read_field':
            report['field'] = field
        elif action == 'read_switch':
            report['switch'] = switch
        else:
            report.update({
                'raw': raw,
                'voltage': voltage,
                'field': field,
                'switch': switch
            })

        return report

    # Example usage:
    # print(ky035_read())                # Full report
    # print(ky035_read('read_field'))    # Only magnetic field strength
    # print(ky035_read('read_switch'))   # Only digital switch state


