"""
ltr390_uv_01.py

MicroPython driver for the LTR390-UV-01 digital UV & ambient light sensor.
Follows the style of veml6075.py, but adapted for the LTR390 (I²C addr 0x53).
"""

from time import ticks_ms
from machine import I2C, Pin

# —— Configuration ——
# I2C parameters for LTR390-UV-01 UV sensor module
from .wiring import LTR390_SDA, LTR390_SCL
LTR390_FREQ = 100_000  # 100 kHz

# LTR390 register addresses and I²C address
_LTR390_ADDR       = 0x53  # 7-bit I²C address
_REG_MAIN_CTRL     = 0x00  # Main control register (enable ALS/UVS) :contentReference[oaicite:0]{index=0}
_REG_MEAS_RATE     = 0x04  # Resolution & data rate :contentReference[oaicite:1]{index=1}
_REG_GAIN          = 0x05  # ALS & UVS gain range :contentReference[oaicite:2]{index=2}
_REG_PART_ID       = 0x06  # Part ID / revision :contentReference[oaicite:3]{index=3}
_REG_MAIN_STATUS   = 0x07  # Main status register :contentReference[oaicite:4]{index=4}
_REG_ALS_DATA      = 0x0D  # ALS data low byte :contentReference[oaicite:5]{index=5}
_REG_UVS_DATA      = 0x10  # UVS data low byte :contentReference[oaicite:6]{index=6}

# Default settings:
#  - MAIN_CTRL: enable both ALS and UVS (bit0 = ALS_EN, bit1 = UVS_EN) → 0x03
#  - MEAS_RATE: default integration time & resolution → 0x05 (e.g. 100 ms, 20-bit)
#  - GAIN: default gain = 1× → 0x00
_DEFAULT_MAIN_CTRL = 0x03
_DEFAULT_MEAS_RATE = 0x05
_DEFAULT_GAIN      = 0x00

class LTR390:
    """
    Helper class for the LTR390-UV-01 ambient & UV sensor.
    Provides raw ALS/UVS readings and simple index estimations.
    """
    def __init__(
            self,
            scl_pin: int = LTR390_SCL,
            sda_pin: int = LTR390_SDA,
            freq:   int = LTR390_FREQ
    ):
        # Initialize I2C bus
        self.i2c = I2C(1, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)

        # Write default configuration
        # Enable both ALS and UVS
        self.i2c.writeto_mem(_LTR390_ADDR,
                             _REG_MAIN_CTRL,
                             bytes([_DEFAULT_MAIN_CTRL]))
        # Set measurement rate (integration time & resolution)
        self.i2c.writeto_mem(_LTR390_ADDR,
                             _REG_MEAS_RATE,
                             bytes([_DEFAULT_MEAS_RATE]))
        # Set gain
        self.i2c.writeto_mem(_LTR390_ADDR,
                             _REG_GAIN,
                             bytes([_DEFAULT_GAIN]))

        self.check_connection()

    def check_connection(self) -> None:
        """
        Raise RuntimeError if the sensor does not respond or part-id read fails.
        """
        try:
            pid = self.i2c.readfrom_mem(_LTR390_ADDR, _REG_PART_ID, 1)[0]
        except Exception as e:
            raise RuntimeError(f"LTR390 self-check failed: {e}")
        # Optionally verify pid matches expected value (see datasheet)

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from the LTR390-UV-01 sensor.

        action:
          - "raw":    return raw ALS and UVS counts
          - "index":  return calculated UV index and lux
          - other/None: return full report

        Returns a dict with:
          - timestamp: ms ticks
          - sensor:    "LTR390"
          - raw_als:   raw ambient light count
          - raw_uvs:   raw UV sensor count
          - lux:       ambient light in lux (approx.)
          - uv_index:  UV index (approx.)
        """
        ts = ticks_ms()

        # Read raw ALS (2 bytes little-endian)
        raw_als = int.from_bytes(
            self.i2c.readfrom_mem(_LTR390_ADDR, _REG_ALS_DATA, 2),
            'little'
        )
        # Read raw UVS (2 bytes little-endian)
        raw_uvs = int.from_bytes(
            self.i2c.readfrom_mem(_LTR390_ADDR, _REG_UVS_DATA, 2),
            'little'
        )

        # Simple conversions (coefficients from typical LTR390 examples)
        lux     = raw_als * 0.5    # ambient light responsivity (lx per count)
        uv_index = raw_uvs * 0.02  # UV index responsivity (UVI per count)

        report = {"timestamp": ts, "sensor": "LTR390"}
        if action == 'raw':
            report.update({'raw_als': raw_als, 'raw_uvs': raw_uvs})
        elif action == 'index':
            report.update({'lux': lux, 'uv_index': uv_index})
        else:
            report.update({
                'raw_als':   raw_als,
                'raw_uvs':   raw_uvs,
                'lux':       lux,
                'uv_index':  uv_index,
            })
        return report
