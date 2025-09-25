from machine import Pin, time_pulse_us
from time import ticks_us, sleep_us

# —— Configuration ——
from .wiring import HCSR04_TRIG, HCSR04_ECHO  # Define pins in wiring

# Default timeout for echo pulse (in microseconds)
DEFAULT_TIMEOUT_US = 30000  # ~5 meters maximum range

class HC_SR04:
    def __init__(
        self,
        trig_pin: int = HCSR04_TRIG,
        echo_pin: int = HCSR04_ECHO,
        timeout_us: int = DEFAULT_TIMEOUT_US
    ):
        # Initialize trigger pin (output) and echo pin (input)
        self.trig = Pin(trig_pin, mode=Pin.OUT)
        self.echo = Pin(echo_pin, mode=Pin.IN)
        self.timeout_us = timeout_us
        # Ensure trigger is low
        self.trig.value(0)
        # Basic self-check
        self.check_connection()

    def check_connection(self):
        """
        Perform a test measurement to ensure sensor is responding.
        Raises RuntimeError on timeout.
        """
        pulse = self._send_pulse_and_wait()
        if pulse is None:
            raise RuntimeError("HC-SR04 self-check failed: no echo received")

    def _send_pulse_and_wait(self):
        """
        Send ultrasonic pulse and wait for echo, returning pulse duration in microseconds.
        Returns None on timeout.
        """
        # Trigger a 10µs pulse
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        try:
            # Measure the length of the high pulse on echo pin
            pulse_time = time_pulse_us(self.echo, 1, self.timeout_us)
            return pulse_time
        except OSError:
            # Timeout waiting for echo
            return None

    def read_distance(self) -> float:
        """
        Perform a measurement and return distance to the nearest object in centimeters.
        Raises RuntimeError on timeout.
        """
        pulse = self._send_pulse_and_wait()
        if pulse is None:
            raise RuntimeError("HC-SR04 read timeout: no echo received within {} µs".format(self.timeout_us))
        # Convert time to distance: sound speed ~343 m/s => 0.0343 cm/µs
        distance_cm = (pulse * 0.0343) / 2
        return distance_cm

    async def do_read(self, action: str):
        """
        Read data based on action:
          - read_distance: return only distance
          - any other: default to full read (distance)

        Returns a dict with timestamp, sensor name, and requested data field or an error.
        """
        ts = ticks_us()
        try:
            if action == "read_distance":
                dist = self.read_distance()
                return {
                    "timestamp": ts,
                    "sensor": "HC-SR04",
                    "distance_cm": dist
                }
            else:
                # Default: distance measurement
                dist = self.read_distance()
                return {
                    "timestamp": ts,
                    "sensor": "HC-SR04",
                    "distance_cm": dist
                }
        except Exception as e:
            return {"timestamp": ticks_us(), "error": str(e)}
