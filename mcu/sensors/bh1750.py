from __future__ import annotations

from collections import OrderedDict
from time import ticks_ms
from typing import Optional
from machine import I2C, Pin

# —— Configuration ————————————————————————————————————————————————
from .wiring import BH1750_SCL_PIN, BH1750_SDA_PIN


# BH1750 commands
BH1750_I2C_FREQ = 100_000
BH1750_ADDR     = 0x23
_POWER_ON = 0x01
_RESET = 0x07
_CONT_H_RES = 0x10   # Continuous measurement, high resolution mode (1 lx per bit)


class _MinimalBH1750:
    """Minimal I2C implementation, compatible with the Micropython `bh1750` library interface."""

    def __init__(self, i2c: I2C, addr: int = BH1750_ADDR):
        self.i2c = i2c
        self.addr = addr
        # Power on the sensor
        self.i2c.writeto(self.addr, bytes([_POWER_ON]))
        # Reset the sensor data register
        self.i2c.writeto(self.addr, bytes([_RESET]))
        # Set to continuous high-resolution mode by default
        self.i2c.writeto(self.addr, bytes([_CONT_H_RES]))

    def luminance(self) -> float:
        """Read two bytes from sensor and convert to lux. lux = raw / 1.2"""
        data = self.i2c.readfrom(self.addr, 2)
        raw = (data[0] << 8) | data[1]
        lux = raw / 1.2
        return lux

    def raw(self) -> int:
        """Return raw 16-bit light level count."""
        data = self.i2c.readfrom(self.addr, 2)
        return (data[0] << 8) | data[1]


class BH1750:
    """BH1750 lux sensor driver with MCP-style do_read()."""

    def __init__(
        self,
        scl_pin: int = BH1750_SCL_PIN,
        sda_pin: int = BH1750_SDA_PIN,
        freq: int = BH1750_I2C_FREQ,
        addr: int = BH1750_ADDR,
    ) -> None:
        # Initialize I2C bus
        if isinstance(I2C, type):  # Running on MicroPython environment
            self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
        else:
            self.i2c = None  # type: ignore

        # Select underlying driver implementation
        driver: Optional[object] = None
        if self.i2c is not None:
            try:
                import bh1750 as bhlib  # type: ignore
                driver = bhlib.BH1750(self.i2c, addr=addr)
            except (ImportError, AttributeError):
                driver = _MinimalBH1750(self.i2c, addr)
        self.sensor = driver
        self.addr = addr
        self.check_connection()

    # ------------------------------------------------------------------
    def check_connection(self):
        """Verify sensor connectivity by performing a sample read."""
        try:
            _ = self.sensor.luminance()  # type: ignore
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"BH1750 self-check failed: {exc}") from exc

    # ------------------------------------------------------------------
    async def do_read(self, action: str | None = None):
        """Acquire light level measurement.

        action:
          • "read_lux"   -> return lux as float
          • "read_raw"   -> return raw 16-bit count
          • other/None    -> return full OrderedDict report
        """
        ts = ticks_ms()
        try:
            lux = self.sensor.luminance()  # type: ignore
        except Exception as exc:  # pylint: disable=broad-except
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "BH1750"),
                ("error", str(exc)),
            ])

        if action == "read_lux":
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "BH1750"),
                ("lux", lux),
            ])
        elif action == "read_raw":
            raw = self.sensor.raw() if hasattr(self.sensor, "raw") else None  # type: ignore
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "BH1750"),
                ("raw", raw),
            ])
        else:
            raw = self.sensor.raw() if hasattr(self.sensor, "raw") else None  # type: ignore
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "BH1750"),
                ("lux", lux),
                ("raw", raw),
            ])

# ---------------------------- Usage example -----------------------------
# i2c_lux = BH1750()
# full_report = await i2c_lux.do_read()           # full report
# lux_value   = await i2c_lux.do_read("read_lux")  # lux only
