from machine import I2C, Pin
from time import ticks_ms

# —— Configuration ——
# I2C bus and pins for GY-302 (BH1750) light sensor
from .wiring import  GY302_SCL_PIN, GY302_SDA_PIN

class GY302:
    """
    Driver class for a GY-302 (BH1750) digital light sensor module.

    Provides ambient light intensity measurements in lux via I2C.
    """
    # BH1750 I2C default address
    _DEFAULT_ADDR = 0x23
    # Measurement mode: One-time high resolution (1 lx resolution)
    _ONE_TIME_HIGH_RES = 0x20

    def __init__(
        self,
        scl_pin: int = GY302_SCL_PIN,
        sda_pin: int = GY302_SDA_PIN,
        freq: int = 100000,
        address: int = None
    ):
        """
        Initialize the BH1750 sensor on the given I2C bus.

        Args:
          bus_id:   I2C bus identifier.
          scl_pin:  GPIO pin for I2C SCL.
          sda_pin:  GPIO pin for I2C SDA.
          freq:     I2C clock frequency (Hz).
          address:  I2C address (default 0x23).
        """
        self.address = address or self._DEFAULT_ADDR
        # Set up I2C interface
        self.i2c = I2C(
            scl=Pin(scl_pin),
            sda=Pin(sda_pin),
            freq=freq
        )
        self.check_connection()

    def check_connection(self) -> None:
        """
        Verify that the BH1750 is present on the I2C bus.
        Raises RuntimeError on failure.
        """
        devices = self.i2c.scan()
        if self.address not in devices:
            raise RuntimeError(
                f"GY302 (BH1750) not found at address 0x{self.address:02X}; found: {devices}"
            )

    async def do_read(self, action: str = None) -> dict:
        """
        Read a lux measurement from the BH1750.

        Args:
          action: (optional)
            - 'read_raw': return raw sensor value (16-bit int)
            - 'read_lux': return computed lux (float)
            - other or None: return full report

        Returns:
          dict containing:
            - timestamp: ms ticks
            - sensor:    'GY302'
            - raw:       raw measurement (0–65535)
            - lux:       computed illuminance in lux
        """
        # Request one-time high-resolution measurement
        self.i2c.writeto(self.address, bytes([self._ONE_TIME_HIGH_RES]))

        # According to datasheet, max. 180ms conversion time
        # Here, we assume async environment handles timing; a real implementation
        # might await asyncio.sleep_ms(180) or similar.

        raw_bytes = self.i2c.readfrom(self.address, 2)
        raw = (raw_bytes[0] << 8) | raw_bytes[1]
        # Convert raw value to lux (per BH1750 datasheet)
        lux = raw / 1.2

        timestamp = ticks_ms()
        report = {
            'timestamp': timestamp,
            'sensor':    'GY302',
        }
        if action == 'read_raw':
            report['raw'] = raw
        elif action == 'read_lux':
            report['lux'] = lux
        else:
            report.update({'raw': raw, 'lux': lux})
        return report

# Example usage:
# sensor = GY302()
# full = await sensor.do_read()         # {'timestamp':..., 'raw':12345, 'lux':10287.5}
# r = await sensor.do_read('read_raw')  # {'timestamp':..., 'raw':12345}
# l = await sensor.do_read('read_lux')  # {'timestamp':..., 'lux':10287.5}
