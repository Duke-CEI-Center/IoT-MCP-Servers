from __future__ import annotations
from collections import OrderedDict
from time import ticks_ms
from typing import Optional, List
from machine import I2C, Pin


# —— Wiring constants ————————————————————————————————————————————
from .wiring import (
    PN532_SCL_PIN,
    PN532_SDA_PIN,
    PN532_RST_PIN,
)
PN532_I2C_FREQ = 100_000

# ---------------------------------------------------------------------------
# Fallback minimal driver (I²C) if pn532 lib unavailable
# ---------------------------------------------------------------------------
class _MinimalPN532:
    def __init__(self, i2c: I2C, rst: Optional[Pin] = None, addr: int = 0x24):
        self.i2c = i2c
        self.addr = addr  # 0x24 when R/W bit cleared (0x48 shifted)
        self._init_module(rst)

    # Low-level helpers --------------------------------------------------
    def _w(self, data: bytes):  # write with preamble 0x00 0x00 0xFF
        length = len(data) + 1
        lcs = (0x100 - length) & 0xFF
        frame = b"\x00\x00\xFF" + bytes([length, lcs]) + data
        dcs = (0x100 - sum(data) & 0xFF)
        frame += bytes([dcs, 0x00])
        self.i2c.writeto(self.addr, frame)

    def _r(self, nbytes: int) -> bytes:
        return self.i2c.readfrom(self.addr, nbytes)

    def _init_module(self, rst: Optional[Pin]):
        # hardware reset if available
        if rst is not None and isinstance(Pin, type):
            rst.value(0)
            from time import sleep_ms
            sleep_ms(20)
            rst.value(1)
            sleep_ms(20)
        # wakeup frame (SAMConfiguration later)
        self._w(b"\xD4\x14\x01\x14\x01\x00")

    # Public minimal API -----------------------------------------------
    def firmware(self) -> List[int]:
        self._w(b"\xD4\x02")  # GetFirmwareVersion
        resp = self._r(22)[13:17]  # skip to data (IC Ver Rev)
        return list(resp)

    def read_passive_target(self, timeout_ms: int = 750):
        from time import ticks_ms, ticks_diff, sleep_ms
        self._w(b"\xD4\x4A\x01\x00")  # InListPassiveTarget, 1 card, 106 kbps
        start = ticks_ms()
        while ticks_diff(ticks_ms(), start) < timeout_ms:
            hdr = self._r(7)
            if hdr.endswith(b"\x00\xFF"):
                sleep_ms(5)
                continue  # Not ready
            data = self._r(19)
            if data[0] == 0xD5 and data[1] == 0x4B and data[3] > 0:
                uid_len = data[4]
                return data[5 : 5 + uid_len]
            sleep_ms(10)
        return None


# ---------------------------------------------------------------------------
class PN532:
    """PN532 driver exposing MCP-style async do_read()."""

    def __init__(
        self,
        scl_pin: int = PN532_SCL_PIN,
        sda_pin: int = PN532_SDA_PIN,
        rst_pin: Optional[int] = PN532_RST_PIN,
        freq: int = PN532_I2C_FREQ,
    ) -> None:
        # — I²C init —
        if isinstance(I2C, type):
            self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
        else:
            self.i2c = None  # type: ignore

        self.rst = Pin(rst_pin, Pin.OUT, value=1) if (rst_pin and isinstance(Pin, type)) else None  # type: ignore

        # Prefer full library if present
        driver = None
        if self.i2c is not None:
            try:
                from pn532_i2c import PN532_I2C  # type: ignore
                import pn532  # type: ignore

                driver = PN532_I2C(self.i2c, reset=self.rst, debug=False)
                driver.SAM_configuration()  # Normal mode
            except ImportError:
                driver = _MinimalPN532(self.i2c, self.rst)
        self.nfc = driver
        self.check_connection()

    # ------------------------------------------------------------------
    def check_connection(self):
        try:
            _ = self.nfc.firmware() if hasattr(self.nfc, "firmware") else None  # type: ignore
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"PN532 self-check failed: {exc}") from exc

    # ------------------------------------------------------------------
    async def do_read(self, action: str | None = None):
        """Perform requested PN532 operation.

        Actions:
          • "read_uid"      – passive polling, return UID list or None
          • "read_firmware" – IC+Ver+Rev list
          • None/other      – full report {firmware, uid}
        """
        ts = ticks_ms()

        # Firmware version ------------------------------------------------
        try:
            fw = self.nfc.firmware() if hasattr(self.nfc, "firmware") else None  # type: ignore
        except Exception as exc:
            fw = None
            err_msg = str(exc)
        else:
            err_msg = None

        # UID polling when requested / default ----------------------------
        uid = None
        if action in (None, "read_uid"):
            try:
                uid = self.nfc.read_passive_target(timeout_ms=750)  # type: ignore
            except Exception:
                uid = None

        if action == "read_uid":
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "PN532"),
                ("uid", uid),
            ])
        elif action == "read_firmware":
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "PN532"),
                ("firmware", fw),
            ])
        else:
            rep = OrderedDict([
                ("timestamp", ts),
                ("sensor", "PN532"),
                ("firmware", fw),
                ("uid", uid),
            ])
            if err_msg:
                rep["error"] = err_msg
            return rep


# ----------------------- Usage (MicroPython REPL) -----------------------
# nfc = PN532()
# print(await nfc.do_read())           # full report (firmware + uid)
# print(await nfc.do_read('read_uid')) # UID only
