import uasyncio as asyncio  # Asynchronous IO library for microcontrollers
from machine import Pin  # Hardware interfaces
from time import ticks_ms  # Millisecond timestamp
from micropython import const
import onewire, ds18x20

# —— Configuration ——
from .wiring import DS18X20_PIN

_RESOLUTION_CONFIG = {
    9:  const(0x1F),  # 9-bit  -> R1R0 = 00
    10: const(0x3F),  # 10-bit -> R1R0 = 01
    11: const(0x5F),  # 11-bit -> R1R0 = 10
    12: const(0x7F),  # 12-bit -> R1R0 = 11
}



# -----------------------------------------------------------------------------
# Sensor read helper
# -----------------------------------------------------------------------------
class DS18X20:
    def __init__(
        self,
        pin_number: int = DS18X20_PIN,
        pull_up: bool = False,
        resolution: int = 9,
        th: int = 30,
        tl: int = 10,
    ) -> None:
        """
        Initialize the DS18B20 manager and configure all detected sensors:
          - resolution: bit resolution (9, 10, 11, or 12)
          - th: high alarm threshold (-55 to +125 °C)
          - tl: low alarm threshold  (-55 to +125 °C)
        """
        # 1. Set up the OneWire bus on the given pin
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.ow = onewire.OneWire(Pin(pin_number, *pin_kwargs))
        self.sensor = ds18x20.DS18X20(self.ow)

        # 2. Scan and store all ROM codes
        self.roms_raw = self.sensor.scan()
        self.roms_hex = [bytes(r).hex() for r in self.roms_raw]

        self.update_config(resolution, th, tl)
        self.check_connection()

    def check_connection(self):
        try:
            self.sensor.convert_temp()
            _ = {
            hex_key: self.sensor.read_temp(raw_rom)
            for raw_rom, hex_key in zip(self.roms_raw, self.roms_hex)
            }
        except Exception as e:
            raise RuntimeError(f"DS18X20 self-check failed: {e}")

    async def update_config(
        self,
        resolution: int = 9,
        th: int = 30,
        tl: int = 10,
    ) -> None:
        """
        Re-configure all sensors at runtime:
          - resolution: bit resolution (9, 10, 11, 12)
          - th: high alarm threshold (-55 to +125 °C)
          - tl: low alarm threshold  (-55 to +125 °C)
        """
        # 1. Validate resolution
        if resolution not in _RESOLUTION_CONFIG:
            raise ValueError(f"Unsupported resolution: {resolution}")
        config_byte = _RESOLUTION_CONFIG[resolution]

        # 2. For each sensor, write scratchpad then copy to EEPROM
        for rom in self.roms_raw:
            # -- WRITE SCRATCHPAD (0x4E)
            self.ow.reset()                 # reset bus
            self.ow.select_rom(rom)         # select this device
            self.ow.writebyte(0x4E)         # WRITE SCRATCHPAD
            self.ow.writebyte(th & 0xFF)    # write TH
            self.ow.writebyte(tl & 0xFF)    # write TL
            self.ow.writebyte(config_byte)  # write Config

            # -- COPY SCRATCHPAD (0x48)
            self.ow.reset()                 # reset bus again
            self.ow.select_rom(rom)
            self.ow.writebyte(0x48)         # COPY SCRATCHPAD

            # wait for EEPROM write (max 10 ms)
            await asyncio.sleep_ms(20)


    async def do_read(self, action: str):
        """
        Read data from one or more DS18B20 sensors based on action:
          - read_temp:       return temperatures for all sensors
          - read_rom:        return list of sensor ROM codes
          - read_scratchpad: return raw scratchpad bytes for each sensor
          - read_config:     return configuration register for each sensor
          - any other:       return a full report of all above
        Returns a dict with:
          - timestamp: current ticks_ms()
          - requested fields (temperatures, roms, scratchpads, configs)
          - or error on failure
        """
        ts = ticks_ms()
        try:
            # Trigger temperature conversion on all devices
            self.sensor.convert_temp()
            # Wait max conversion time for 12-bit resolution if needed
            # time.sleep_ms(750)

            # Read temperatures using raw ROMs, format values with one decimal and °C
            temperatures = {
                hex_key: self.sensor.read_temp(raw_rom)
                for raw_rom, hex_key in zip(self.roms_raw, self.roms_hex)
            }
            self.ow.reset()
            self.ow.writebyte(0xEC)  # ALARM SEARCH
            alarmed_roms = [bytes(r).hex() for r in self.ow.scan()]

        except Exception as e:
            return {
                "timestamp": ts,
                "error": str(e)}

        # Handle each action
        if action == "read_temp":
            return {
                "timestamp": ts,
                "sensor": "DS18B20",
                "temperatures": temperatures,
            }

        elif action == "read_rom":
            # Return hex codes for clients
            return {
                "timestamp": ts,
                "sensor": "DS18B20",
                "roms": self.roms_hex,
            }

        elif action == "read_config":
            # Extract configuration byte (byte index 4) from scratchpad
            configs = {}
            for raw_rom, hex_key in zip(self.roms_raw, self.roms_hex):
                sp = self.sensor.read_scratch(raw_rom)
                configs[hex_key] = sp[4]
            return {
                "timestamp": ts,
                "sensor": "DS18B20",
                "configs": configs,
            }

        elif action =="read_alarmed_roms":
            return {
                "timestamp": ts,
                "sensor": "DS18B20",
                "alarmed_roms": alarmed_roms,
            }

        elif action == "read_scratchpad":
            # Read raw 9-byte scratchpad for each sensor
            scratchpads = {
                hex_key: self.sensor.read_scratch(raw_rom)
                for raw_rom, hex_key in zip(self.roms_raw, self.roms_hex)
            }
            return {
                "timestamp": ts,
                "sensor": "DS18B20",
                "scratchpads": scratchpads
            }

        else:
            # Default: full report
            configs = {}
            for raw_rom, hex_key in zip(self.roms_raw, self.roms_hex):
                sp = self.sensor.read_scratch(raw_rom)
                configs[hex_key] = sp[4]
            return {
                "timestamp":     ts,
                "sensor":        "DS18B20",
                "roms":          self.roms_hex,
                "temperatures":  temperatures,
                "configs":       configs,
                "alarmed_roms":  alarmed_roms
            }