import logging
from typing import Any
import time

logger = logging.getLogger(__name__)

class BaseSensor:
    def __init__(self, name: str):
        self.name = name
        self.last_state = None

    def read_state(self) -> Any:
        """Liest den Sensor aus. MUSS überschrieben werden."""
        raise NotImplementedError("Subklassen müssen read_state() implementieren")

    def get_update_if_changed(self) -> str:
        """Gibt einen Text-String zurück, falls sich der Status geändert hat. Sonst None."""
        current_state = self.read_state()
        
        if current_state is not None and current_state != self.last_state:
            self.last_state = current_state
            return self.format_message(current_state)
        return None

    def format_message(self, state: Any) -> str:
        return f"Sensor {self.name} meldet: {state}"


if __name__ == "__main__":
    from touch_sensor import TouchSensor
    from flex_sensor import FlexSensor
    from gyro_sensor import OrientationSensor

    logging.basicConfig(level=logging.INFO)
    print("\n--- Starte Sensor-Test ---")
    print("Drücke STRG+C um den Test zu beenden.\n")

    touch = TouchSensor("TouchSensor Test")
    flex = FlexSensor("FlexSensor Test", gpio_pin=17)
    orientation = OrientationSensor("GyroSensor Test")

    try:
        while True:
            touch_update = touch.get_update_if_changed()
            if touch_update:
                print(f"📡 {touch_update}")

            flex_update = flex.get_update_if_changed()
            if flex_update:
                print(f"📡 {flex_update}")

            orientation_update = orientation.get_update_if_changed()
            if orientation_update:
                print(f"📡 {orientation_update}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nTest beendet. Tschüss!")