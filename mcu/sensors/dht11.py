from collections import OrderedDict
from time import ticks_ms
from machine import Pin
import dht

# —— Configuration ——
from .wiring import DHT11_PIN


class DHT11:
    def __init__(
            self,
            pin_number: int = DHT11_PIN,
            pull_up: bool = False
    ):
        pin_kwargs = (Pin.IN, Pin.PULL_UP) if pull_up else (Pin.IN,)
        self.sensor = dht.DHT11(Pin(pin_number, *pin_kwargs))
        self.check_connection()

    def check_connection(self) -> None:
        """Raise RuntimeError if sensor does not respond."""
        try:
            self.sensor.measure()
            _ = self.sensor.temperature()
            _ = self.sensor.humidity()
        except Exception as e:
            raise RuntimeError(f"DHT11 self-check failed: {e}")


    async def do_read(self, action: str):
        """
        Read from DHT11 sensor and return dict
        supported actions: 'read_all', 'read_temp', 'read_hum'
        """
        timestamp = ticks_ms()
        try:
            self.sensor.measure()
            temp = self.sensor.temperature()
            hum = self.sensor.humidity()
        except Exception as e:
            return OrderedDict([
                ("timestamp", timestamp),
                ("sensor", "DHT11"),
                ("error", str(e)),
            ])

        if action == "read_temp":
            return OrderedDict([
                ("timestamp", timestamp),
                ("sensor", "DHT11"),
                ("temperature", temp),
            ])
        elif action == "read_hum":
            return OrderedDict([
                ("timestamp", timestamp),
                ("sensor", "DHT11"),
                ("humidity", hum),
            ])
        else:  # read_all or any other
            return OrderedDict([
                ("timestamp", timestamp),
                ("sensor", "DHT11"),
                ("temperature", temp),
                ("humidity", hum),
            ])
