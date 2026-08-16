import logging
from typing import Any, Dict, Optional
import time

logger = logging.getLogger(__name__)

class BaseSensor:
    def __init__(self, name: str):
        self.name = name
        self.last_state = None

    def read_state(self) -> Any:
        """Liest den Sensor aus. MUSS überschrieben werden."""
        raise NotImplementedError("Subklassen müssen read_state() implementieren")

    def format_event(self, state: Any) -> Optional[Dict[str, Any]]:
        """Optionales strukturiertes Event für Backend-Routing."""
        return None

    def get_event_if_changed(self) -> Optional[Dict[str, Any]]:
        """Gibt ein strukturiertes Event zurück, falls sich der Status geändert hat."""
        current_state = self.read_state()
        if current_state is not None and current_state != self.last_state:
            self.last_state = current_state
            return self.format_event(current_state)
        return None

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
            touch_event = touch.get_event_if_changed()
            if touch_event:
                print(f"🧩 EVENT Touch: {touch_event}")

            flex_event = flex.get_event_if_changed()
            if flex_event:
                print(f"🧩 EVENT Flex: {flex_event}")

            orientation_event = orientation.get_event_if_changed()
            if orientation_event:
                print(f"🧩 EVENT Gyro: {orientation_event}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nTest beendet. Tschüss!")