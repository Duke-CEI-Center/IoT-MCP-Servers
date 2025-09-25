# ds1307rtc.py
from machine import I2C, Pin
from time import ticks_ms

# —— Configuration ——
# I2C parameters for DS1307RTC module
from .wiring import (
    DS1307RTC_SDA_PIN,
    DS1307RTC_SCL_PIN,
    DS1307RTC_I2C_FREQ,
    DS1307RTC_SQW_PIN
)

# DS1307 I2C address
_DS1307_ADDR = 0x68


def _bcd2dec(bcd: int) -> int:
    """Convert binary-coded decimal to integer."""
    return (bcd // 16) * 10 + (bcd % 16)


def _dec2bcd(dec: int) -> int:
    """Convert integer to binary-coded decimal."""
    return (dec // 10) * 16 + (dec % 10)


class DS1307RTC:
    """
    Driver for DS1307 RTC module via I2C.
    Supports reading and writing datetime, and reading SQW output.
    """
    def __init__(
        self,
        scl_pin: int = DS1307RTC_SCL_PIN,
        sda_pin: int = DS1307RTC_SDA_PIN,
        freq: int    = DS1307RTC_I2C_FREQ,
        addr: int    = _DS1307_ADDR
    ):
        # Initialize I2C bus
        self.i2c = I2C(
            scl=Pin(scl_pin),
            sda=Pin(sda_pin),
            freq=freq
        )
        self.addr = addr
        self.check_connection()

    def check_connection(self) -> None:
        """
        Verify communication by reading the seconds register.
        Raises RuntimeError on failure.
        """
        try:
            self.i2c.readfrom_mem(self.addr, 0x00, 1)
        except Exception as e:
            raise RuntimeError(f"DS1307RTC self-check failed: {e}")

    def read_datetime(self) -> tuple:
        """
        Read current datetime from DS1307.
        Returns tuple: (year, month, day, weekday, hour, minute, second).
        """
        data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        sec  = _bcd2dec(data[0] & 0x7F)
        minute = _bcd2dec(data[1])
        hour = _bcd2dec(data[2] & 0x3F)
        weekday = _bcd2dec(data[3])
        day = _bcd2dec(data[4])
        month = _bcd2dec(data[5])
        year = 2000 + _bcd2dec(data[6])
        return year, month, day, weekday, hour, minute, sec

    def write_datetime(self, dt: tuple) -> None:
        """
        Write datetime to DS1307.
        dt tuple: (year, month, day, weekday, hour, minute, second).
        Year must be >=2000.
        """
        yr, mo, d, wd, hr, mi, sec = dt
        buf = bytearray(7)
        buf[0] = _dec2bcd(sec)
        buf[1] = _dec2bcd(mi)
        buf[2] = _dec2bcd(hr)
        buf[3] = _dec2bcd(wd)
        buf[4] = _dec2bcd(d)
        buf[5] = _dec2bcd(mo)
        buf[6] = _dec2bcd(yr - 2000)
        self.i2c.writeto_mem(self.addr, 0x00, buf)

    async def do_read(self, action: str = None) -> dict:
        """
        Read data from DS1307RTC with a unified interface.

        action options:
          - 'read_datetime': return full tuple
          - 'read_date':     return date dict
          - 'read_time':     return time dict
          - 'read_sqw':      return SQW pin status
          - other or None:   return full report

        Returns dict with keys:
          - timestamp: current ticks_ms()
          - sensor:    'DS1307RTC'
          - datetime:  full tuple
          - date:      dict(year, month, day, weekday)
          - time:      dict(hour, minute, second)
          - sqw:       bool status of SQW pin
        """
        ts = ticks_ms()
        yr, mo, d, wd, hr, mi, sec = self.read_datetime()
        # Read SQW pin if available
        try:
            sqw_pin = Pin(DS1307RTC_SQW_PIN, Pin.IN)
            sqw = bool(sqw_pin.value())
        except Exception:
            sqw = None

        report = {'timestamp': ts, 'sensor': 'DS1307RTC'}
        if action == 'read_datetime':
            report['datetime'] = (yr, mo, d, wd, hr, mi, sec)
        elif action == 'read_date':
            report['date'] = {'year': yr, 'month': mo, 'day': d, 'weekday': wd}
        elif action == 'read_time':
            report['time'] = {'hour': hr, 'minute': mi, 'second': sec}
        elif action == 'read_sqw':
            report['sqw'] = sqw
        else:
            report.update({
                'datetime': (yr, mo, d, wd, hr, mi, sec),
                'date': {'year': yr, 'month': mo, 'day': d, 'weekday': wd},
                'time': {'hour': hr, 'minute': mi, 'second': sec}
            })
            if sqw is not None:
                report['sqw'] = sqw
        return report

# End of ds1307rtc.py
