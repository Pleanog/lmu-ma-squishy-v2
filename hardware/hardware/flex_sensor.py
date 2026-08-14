import logging
from gpiozero import DigitalInputDevice
from .base_sensor import BaseSensor

logger = logging.getLogger(__name__)

class FlexSensor(BaseSensor):
    def __init__(self, name: str, gpio_pin: int = 17):
        super().__init__(name)
        try:
            # DigitalInputDevice liest High (1) oder Low (0)
            self.sensor_pin = DigitalInputDevice(gpio_pin)
            logger.info(f"Biegesensor '{self.name}' an GPIO {gpio_pin} initialisiert.")
        except Exception as e:
            logger.error(f"Fehler bei Biegesensor: {e}")
            self.sensor_pin = None

    def read_state(self):
        if self.sensor_pin is None:
            return self.last_state

        # Je nach Verkabelung ist das Signal 1 wenn gebogen, oder 0 wenn gebogen.
        # Falls es falsch herum reagiert, ändere unten "is_active" zu "not is_active".
        is_bent = not self.sensor_pin.is_active

        if is_bent:
            return "BENT"
        else:
            return "RELEASED"

    def format_message(self, state):
        if state == "BENT":
            return f"Squishy wird gedrückt/gebogen an: {self.name}."
        elif state == "RELEASED":
            return f"Das Drücken an {self.name} hat aufgehört."
        return None 