from time import ticks_ms  # Millisecond timestamp
from machine import ADC, Pin  # Hardware interfaces

# —— Configuration ——
# Analog input pin for the KY-018 photoresistor (LDR) module
from .wiring import KY018_PIN

class KY018:
    """
    Helper class for the KY-018 photoresistor sensor module.
    Reads ambient light level via an analog input.
    """
    def __init__(
            self,
            pin_number: int = KY018_PIN,
            attenuation: ADC.ATTN = ADC.ATTN_11DB
    ):
        # Configure ADC on the given pin
        self.adc = ADC(Pin(pin_number))
        # Set attenuation (full-scale voltage range)
        try:
            self.adc.atten(attenuation)
        except Exception:
            # Some ports may not support attenuation
            pass
        self.check_connection()

    def check_connection(self) -> None:
        """
        Raise RuntimeError if the ADC does not respond.
        """
        try:
            _ = self.adc.read()  # Try a sample read
        except Exception as e:
            raise RuntimeError(f"KY018 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the KY-018 photoresistor sensor module.

        action:
          - "read_raw":   return raw ADC reading (integer)
          - "read_pct":   return percentage of full scale (0.0–100.0)
          - other or None: return full report with both fields

        Returns:
          dict containing:
            - timestamp: ms ticks
            - sensor:    "KY018"
            - raw:       raw ADC value
            - pct:       normalized percentage
        """
        ts = ticks_ms()
        raw = self.adc.read()
        # On a 12-bit ADC this ranges 0–4095; adjust if different
        try:
            pct = (raw / 4095) * 100.0
        except Exception:
            pct = None

        report = {"timestamp": ts, "sensor": "KY018"}
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_pct':
            report['pct'] = pct
        else:
            report.update({'raw': raw, 'pct': pct})
        return report
