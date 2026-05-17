# hardware/led_actuator.py
import RPi.GPIO as GPIO
import asyncio

class LedActuator:
    def __init__(self, pin: int):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.current_state = False

    def set_state(self, state: bool):
        """Sets the LED on (True) or off (False)."""
        if state != self.current_state:
            GPIO.output(self.pin, GPIO.HIGH if state else GPIO.LOW)
            self.current_state = state
            print(f"LED on pin {self.pin} set to {'ON' if state else 'OFF'}")

    async def blink(self, count: int, delay: float):
        """Makes the LED blink for a given count."""
        for _ in range(count):
            self.set_state(True)
            await asyncio.sleep(delay)
            self.set_state(False)
            await asyncio.sleep(delay)
        print(f"LED on pin {self.pin} finished blinking.")