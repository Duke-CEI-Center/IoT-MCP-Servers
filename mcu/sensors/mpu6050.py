from machine import Pin, I2C, SoftI2C
from time import ticks_ms, sleep_ms
from math import sqrt, atan2

# —— Configuration ——
from .wiring import MPU6050_SCL, MPU6050_SDA
DEFAULT_FREQ = 400000

# MPU-6050 Registers and Constants
_PWR_MGMT_1       = 0x6B
_ACCEL_XOUT0      = 0x3B
_TEMP_OUT0        = 0x41
_GYRO_XOUT0       = 0x43
_ACCEL_CONFIG     = 0x1C
_GYRO_CONFIG      = 0x1B
_MPU6050_ADDRESS  = 0x68

# Scale Modifiers
_GRAVITY_MS2      = 9.80665
_ACC_SCLR_2G      = 16384.0
_ACC_SCLR_4G      = 8192.0
_ACC_SCLR_8G      = 4096.0
_ACC_SCLR_16G     = 2048.0
_GYR_SCLR_250DEG  = 131.0
_GYR_SCLR_500DEG  = 65.5
_GYR_SCLR_1000DEG = 32.8
_GYR_SCLR_2000DEG = 16.4

# Pre-defined ranges
_ACC_RNG_2G       = 0x00
_ACC_RNG_4G       = 0x08
_ACC_RNG_8G       = 0x10
_ACC_RNG_16G      = 0x18
_GYR_RNG_250DEG   = 0x00
_GYR_RNG_500DEG   = 0x08
_GYR_RNG_1000DEG  = 0x10
_GYR_RNG_2000DEG  = 0x18

_maxFails = 3
error_msg = "\nError \n"
i2c_err_str = "MPU6050 could not communicate at address 0x{:02X}, check wiring"

# Helper to convert two bytes to signed int
def _signed_int(data):
    val = int.from_bytes(data, 'big')
    if val >= 0x8000:
        return -((65535 - val) + 1)
    return val

class MPU6050:
    def __init__(
        self,
        scl_num: int = MPU6050_SCL,
        sda_num: int = MPU6050_SDA,
        freq: int = DEFAULT_FREQ
    ):
        # Use SoftI2C to allow any pins
        self.i2c = SoftI2C(scl=Pin(scl_num), sda=Pin(sda_num), freq=freq)
        self.addr = _MPU6050_ADDRESS
        # Wake up sensor
        try:
            self.i2c.writeto_mem(self.addr, _PWR_MGMT_1, bytes([0x00]))
            sleep_ms(5)
        except Exception as e:
            raise RuntimeError(i2c_err_str.format(self.addr))
        # Query default ranges
        self._accel_range = self.get_accel_range(raw=True)
        self._gyro_range  = self.get_gyro_range(raw=True)

    def _read_raw(self, reg):
        for attempt in range(_maxFails):
            try:
                sleep_ms(10)
                raw = self.i2c.readfrom_mem(self.addr, reg, 6)
                return {
                    'x': _signed_int(raw[0:2]),
                    'y': _signed_int(raw[2:4]),
                    'z': _signed_int(raw[4:6])
                }
            except:
                pass
        # on fail
        print(i2c_err_str.format(self.addr))
        return {'x': float('nan'), 'y': float('nan'), 'z': float('nan')}

    def read_temperature(self):
        try:
            raw = self.i2c.readfrom_mem(self.addr, _TEMP_OUT0, 2)
            temp_raw = _signed_int(raw)
            return (temp_raw / 340) + 36.53
        except:
            print(i2c_err_str.format(self.addr))
            return float('nan')

    def get_accel_range(self, raw=False):
        reg = self.i2c.readfrom_mem(self.addr, _ACCEL_CONFIG, 1)[0]
        if raw:
            return reg
        return { _ACC_RNG_2G:2, _ACC_RNG_4G:4, _ACC_RNG_8G:8, _ACC_RNG_16G:16 }.get(reg, -1)

    def set_accel_range(self, rng):
        self.i2c.writeto_mem(self.addr, _ACCEL_CONFIG, bytes([rng]))
        self._accel_range = rng

    def read_accel_data(self, g=False):
        d = self._read_raw(_ACCEL_XOUT0)
        # determine scaler
        scaler = {
            _ACC_RNG_2G: _ACC_SCLR_2G,
            _ACC_RNG_4G: _ACC_SCLR_4G,
            _ACC_RNG_8G: _ACC_SCLR_8G,
            _ACC_RNG_16G:_ACC_SCLR_16G
        }.get(self._accel_range, _ACC_SCLR_2G)
        x, y, z = d['x']/scaler, d['y']/scaler, d['z']/scaler
        if not g:
            x, y, z = x*_GRAVITY_MS2, y*_GRAVITY_MS2, z*_GRAVITY_MS2
        return {'x': x, 'y': y, 'z': z}

    def read_accel_abs(self, g=False):
        a = self.read_accel_data(g)
        return sqrt(a['x']**2 + a['y']**2 + a['z']**2)

    def get_gyro_range(self, raw=False):
        reg = self.i2c.readfrom_mem(self.addr, _GYRO_CONFIG, 1)[0]
        if raw:
            return reg
        return { _GYR_RNG_250DEG:250, _GYR_RNG_500DEG:500, _GYR_RNG_1000DEG:1000, _GYR_RNG_2000DEG:2000 }.get(reg, -1)

    def set_gyro_range(self, rng):
        self.i2c.writeto_mem(self.addr, _GYRO_CONFIG, bytes([rng]))
        self._gyro_range = rng

    def read_gyro_data(self):
        d = self._read_raw(_GYRO_XOUT0)
        scaler = {
            _GYR_RNG_250DEG: _GYR_SCLR_250DEG,
            _GYR_RNG_500DEG: _GYR_SCLR_500DEG,
            _GYR_RNG_1000DEG:_GYR_SCLR_1000DEG,
            _GYR_RNG_2000DEG:_GYR_SCLR_2000DEG
        }.get(self._gyro_range, _GYR_SCLR_250DEG)
        return {k: v/scaler for k, v in d.items()}

    def read_angle(self):
        a = self.read_accel_data()
        pitch = atan2(a['y'], a['z'])
        roll  = atan2(-a['x'], a['z'])
        return {'x': pitch, 'y': roll}

    async def do_read(self, action):
        ts = ticks_ms()
        try:
            if action == 'read_temp':
                return {'timestamp': ts, 'sensor':'MPU6050', 'temperature': self.read_temperature()}
            if action == 'read_accel':
                return {'timestamp': ts, 'sensor':'MPU6050', 'accel': self.read_accel_data()}
            if action == 'read_gyro':
                return {'timestamp': ts, 'sensor':'MPU6050', 'gyro': self.read_gyro_data()}
            if action == 'read_angle':
                return {'timestamp': ts, 'sensor':'MPU6050', 'tilt': self.read_angle()}
            # default all
            return {
                'timestamp': ts,
                'sensor': 'MPU6050',
                'accel': self.read_accel_data(),
                'gyro': self.read_gyro_data(),
                'temperature': self.read_temperature(),
                'tilt': self.read_angle()
            }
        except Exception as e:
            return {'timestamp': ticks_ms(), 'error': str(e)}
