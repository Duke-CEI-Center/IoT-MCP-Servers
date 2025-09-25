from time import ticks_ms  # Millisecond timestamp
from machine import I2C, Pin

# —— Configuration ——
# I2C parameters for VEML6075 UV sensor module
from .wiring import VEML6075_SDA, VEML6075_SCL
VEML6075_FREQ = 100000

# VEML6075 register addresses and default I2C address
_VEML6075_ADDR = 0x10  # 7-bit I2C address
_REG_CONF = 0x00
_REG_UVA = 0x07
_REG_UVB = 0x09
_REG_UVCOMP1 = 0x0A  # Dark compensation channel 1
_REG_UVCOMP2 = 0x0B  # Dark compensation channel 2

# Default configuration: active, gain 1, integration time 100 ms
_CONF_SETTINGS = 0x00  # Bits[15:0] as per datasheet

class VEML6075:
    """
    Helper class for the VEML6075 UV sensor module.
    Provides raw UVA/UVB readings and basic UV index estimation.
    """
    def __init__(
            self,
            scl_pin: int = VEML6075_SCL,
            sda_pin: int = VEML6075_SDA,
            freq: int = VEML6075_FREQ
    ):
        # Initialize I2C bus
        self.i2c = I2C(1, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
        # Write default configuration
        self.i2c.writeto_mem(_VEML6075_ADDR, _REG_CONF, _CONF_SETTINGS.to_bytes(2, 'little'))
        self.check_connection()

    def check_connection(self) -> None:
        """
        Raise RuntimeError if the sensor does not respond or config read fails.
        """
        try:
            data = self.i2c.readfrom_mem(_VEML6075_ADDR, _REG_CONF, 2)
            _ = int.from_bytes(data, 'little')
        except Exception as e:
            raise RuntimeError(f"VEML6075 self-check failed: {e}")

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the VEML6075 UV sensor module.

        action:
          - "raw":    return raw UVA and UVB counts
          - "index":  return estimated UV index
          - other or None: return full report with all fields

        Returns:
          dict containing:
            - timestamp: ms ticks
            - sensor:    "VEML6075"
            - raw_uva:   raw UVA count
            - raw_uvb:   raw UVB count
            - comp1:     dark compensation 1 count
            - comp2:     dark compensation 2 count
            - uva:       corrected UVA value
            - uvb:       corrected UVB value
            - uv_index:  estimated UV index
        """
        ts = ticks_ms()
        # Read raw registers
        raw_uva = int.from_bytes(self.i2c.readfrom_mem(_VEML6075_ADDR, _REG_UVA, 2), 'little')
        raw_uvb = int.from_bytes(self.i2c.readfrom_mem(_VEML6075_ADDR, _REG_UVB, 2), 'little')
        comp1 = int.from_bytes(self.i2c.readfrom_mem(_VEML6075_ADDR, _REG_UVCOMP1, 2), 'little')
        comp2 = int.from_bytes(self.i2c.readfrom_mem(_VEML6075_ADDR, _REG_UVCOMP2, 2), 'little')

        # Apply dark compensation
        uva_corr = max(raw_uva - comp1, 0)
        uvb_corr = max(raw_uvb - comp2, 0)
        # Simple UV index estimation (coefficients from datasheet)
        uva_val = uva_corr * 0.001111  # UVA responsivity (mW/cm^2 per count)
        uvb_val = uvb_corr * 0.00125   # UVB responsivity (mW/cm^2 per count)
        uv_index = (uva_val + uvb_val) / 2

        report = {"timestamp": ts, "sensor": "VEML6075"}
        if action == 'raw':
            report.update({'raw_uva': raw_uva, 'raw_uvb': raw_uvb})
        elif action == 'index':
            report['uv_index'] = uv_index
        else:
            report.update({
                'raw_uva': raw_uva,
                'raw_uvb': raw_uvb,
                'comp1': comp1,
                'comp2': comp2,
                'uva': uva_val,
                'uvb': uvb_val,
                'uv_index': uv_index,
            })
        return report
