from machine import ADC, Pin
from time import ticks_ms  # Millisecond timestamp

# —— Configuration ——
# ADC input pin for the analog output (AO) of the temperature sensor module
from .wiring import LM35_ADC_PIN
# Digital output pin (DO) from the onboard comparator (over-temperature alarm)
from .wiring import LM35_DO_PIN
# Reference voltage for ADC conversion (in volts)
from .wiring import V_REF

class LM35:
    """
    Driver class for an LM35-based temperature sensor module
    with both analog (AO) and digital (DO) outputs.
    """
    def __init__(
            self,
            adc_pin: int = LM35_ADC_PIN,
            do_pin: int = LM35_DO_PIN,
            v_ref: float = V_REF,
            pull_up: bool = False
    ):
        # Initialize ADC on the specified pin
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.adc = ADC(Pin(adc_pin, *pin_kwargs))
        # Set ADC attenuation if supported
        try:
            self.adc.atten(ADC.ATTN_11DB)
        except AttributeError:
            pass

        # Initialize digital input for the over-temperature alarm
        self.alarm_pin = Pin(do_pin, Pin.IN)
        self.v_ref = v_ref
        self.check_connection()

    def check_connection(self):
        # Verify that ADC and digital pins are responsive
        try:
            _ = self.adc.read()
            _ = self.alarm_pin.value()
        except Exception as e:
            raise RuntimeError(f"LM35 sensor self-check failed: {e}")

    async def do_read(self, mode: str = None) -> dict:
        """
        Acquire data from the sensor module.

        mode options:
          - "raw":         return raw ADC reading (0–4095)
          - "voltage":     return AO voltage in volts
          - "Celsius":     return calculated temperature in °C
          - "alarm":       return digital alarm status (True/False)
          - other or None: full report with all fields

        Returns a dictionary with:
          - timestamp: current ticks_ms()
          - raw:       ADC reading
          - voltage:   voltage at AO pin (V)
          - Celsius:   temperature in °C
          - alarm:     over-temperature alarm status
        """
        timestamp = ticks_ms()
        raw_value = self.adc.read()  # ADC range: 0–4095
        voltage = raw_value / 4095 * self.v_ref
        temperature_c = voltage * 100  # LM35 outputs 10mV per °C
        alarm_status = bool(self.alarm_pin.value())

        report = {"timestamp": timestamp, "sensor": "LM35"}
        if mode == 'raw':
            report['raw'] = raw_value
        elif mode == 'voltage':
            report['voltage'] = voltage
        elif mode == 'celsius':
            report['celsius'] = temperature_c
        elif mode == 'alarm':
            report['alarm'] = alarm_status
        else:
            report.update({
                'raw': raw_value,
                'voltage': voltage,
                'celsius': temperature_c,
                'alarm': alarm_status
            })
        return report

# Usage example:
# sensor = LM35_TEMPERATURE_SENSOR()
# full_report = await sensor.read()         # All fields
# raw_reading = await sensor.read('raw')    # Raw ADC value
# volts = await sensor.read('voltage')      # Voltage value
# temp_c = await sensor.read('celsius')     # Temperature in °C
# alarm = await sensor.read('alarm')        # Alarm status
