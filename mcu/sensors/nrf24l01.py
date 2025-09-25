from __future__ import annotations

from time import ticks_ms
from collections import OrderedDict
from typing import List, Dict, Any
from machine import Pin, SPI  # type: ignore
import nrf24l01  # type: ignore


# —— Configuration ————————————————————————————————————————————————
from .wiring import (
    NRF24_CE_PIN,
    NRF24_CSN_PIN,
    NRF24_SPI_BUS,
    NRF24_SPI_BAUD,
)

# nRF24L01 instruction / register constants (subset) -----------------------
_R_REGISTER = 0x00
_W_REGISTER = 0x20
_NOP = 0xFF
_STATUS = 0x07
_CONFIG = 0x00
_RF_SETUP = 0x06
_EN_AA = 0x01


class NRF24L01P:
    """Minimal RX‑oriented driver exposing an MCP‑friendly `do_read`."""

    # ------------------------------------------------------------------
    def __init__(
        self,
        ce_pin: int = NRF24_CE_PIN,
        csn_pin: int = NRF24_CSN_PIN,
        spi_bus: int | None = NRF24_SPI_BUS,
        spi_baud: int = NRF24_SPI_BAUD,
    ) -> None:
        # 1. Configure SPI
        if isinstance(SPI, type):  # MicroPython available
            self.spi = SPI(spi_bus, baudrate=spi_baud, polarity=0, phase=0)
        else:
            self.spi = None  # desktop stub

        # 2. Control pins (active‑high CE, active‑low CSN)
        if isinstance(Pin, type):
            self.ce = Pin(ce_pin, Pin.OUT, value=0)
            self.csn = Pin(csn_pin, Pin.OUT, value=1)
        else:
            self.ce = self.csn = None  # type: ignore

        # 3. High‑level wrapper (if lib present)
        if nrf24l01 is not None and self.spi is not None and isinstance(Pin, type):
            self.radio = nrf24l01.NRF24L01(
                spi=self.spi,
                csn=self.csn,
                ce=self.ce,
                payload_size=32,
            )
        else:
            self.radio = None

        self.check_connection()

    # ------------------------------------------------------------------
    # Low‑level helpers (bare SPI) ---------------------------------------
    # ------------------------------------------------------------------
    def _spi_xfer(self, buf: bytes | bytearray) -> bytearray:
        """Transfer bytes over SPI and return the response as bytearray."""
        if self.spi is None:
            return bytearray(len(buf))  # dummy
        self.csn(0)
        resp = self.spi.read(len(buf), write=buf)  # type: ignore[arg-type]
        self.csn(1)
        return resp

    def read_register(self, reg: int, n: int = 1) -> bytes:
        return self._spi_xfer(bytes([_R_REGISTER | reg]) + b"\xFF" * n)[1:]

    def write_register(self, reg: int, val: bytes | int) -> None:
        if isinstance(val, int):
            val = bytes([val])
        _ = self._spi_xfer(bytes([_W_REGISTER | reg]) + val)

    # ------------------------------------------------------------------
    def check_connection(self) -> None:
        """Send NOP; STATUS should not be 0x00 or 0xFF if wired right."""
        if self.spi is None:
            return  # PC stub
        self.csn(0)
        status = self.spi.read(1, write=_NOP)[0]  # type: ignore[arg-type]
        self.csn(1)
        if status in (0x00, 0xFF):
            raise RuntimeError("nRF24L01+ not responding. Check wiring & power.")

    # ------------------------------------------------------------------
    async def do_read(self, action: str | None = None) -> Dict[str, Any]:
        """Return radio diagnostics / payload depending on *action*."""
        ts = ticks_ms()

        # If we have high‑level lib, prefer its helpers ------------------
        if self.radio is not None:
            if action == "rx_payload":
                if self.radio.any():
                    return OrderedDict(
                        [
                            ("timestamp", ts),
                            ("sensor", "NRF24L01P"),
                            ("payload", self.radio.recv().hex()),
                        ]
                    )
                return OrderedDict([
                    ("timestamp", ts),
                    ("sensor", "NRF24L01P"),
                    ("payload", None),
                ])

            # fall through to generic status dump

        # Bare‑metal: read STATUS & key config regs ----------------------
        status = self.read_register(_STATUS)[0] if self.spi else 0x00

        if action == "read_status":
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "NRF24L01P"),
                ("status", status),
            ])

        elif action == "read_config":
            cfg = self.read_register(_CONFIG)[0] if self.spi else 0x00
            rf = self.read_register(_RF_SETUP)[0] if self.spi else 0x00
            enaa = self.read_register(_EN_AA)[0] if self.spi else 0x00
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "NRF24L01P"),
                ("config", cfg),
                ("rf_setup", rf),
                ("en_aa", enaa),
            ])

        elif action == "rx_payload":
            # Minimal RX pop (without helper lib): read FIFO status first
            fifo_status = self.read_register(0x17)[0] if self.spi else 0x11
            if fifo_status & 0x01:  # RX_EMPTY
                payload = None
            else:
                # R_RX_PAYLOAD instr (0x61)
                pl = self._spi_xfer(b"\x61" + b"\xFF" * 32)[1:]
                payload = pl.hex()
            return OrderedDict([
                ("timestamp", ts),
                ("sensor", "NRF24L01P"),
                ("payload", payload),
            ])

        # Default full report -------------------------------------------
        cfg = self.read_register(_CONFIG)[0] if self.spi else 0x00
        rf = self.read_register(_RF_SETUP)[0] if self.spi else 0x00
        fifo_status = self.read_register(0x17)[0] if self.spi else 0x11
        rx_empty = bool(fifo_status & 0x01)

        return OrderedDict(
            [
                ("timestamp", ts),
                ("sensor", "NRF24L01P"),
                ("status", status),
                ("config", cfg),
                ("rf_setup", rf),
                ("rx_empty", rx_empty),
            ]
        )


# ---------------------------------------------------------------------------
# Usage example (MicroPython):
# ---------------------------------------------------------------------------
# from sensors.nrf24l01p import NRF24L01P
# radio = NRF24L01P()
# status = await radio.do_read("read_status")
# print(status)
# if not status["rx_empty"]:
#     print(await radio.do_read("rx_payload"))
