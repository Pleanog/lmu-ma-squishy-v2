import logging
from typing import Any

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
        
        if current_state != self.last_state:
            self.last_state = current_state
            return self.format_message(current_state)
        return None

    def format_message(self, state: Any) -> str:
        """Formatiert den Status für Gemini."""
        return f"Sensor {self.name} meldet: {state}"


# --- SIMULIERTE SENSOREN ---

import random

class TouchSensor(BaseSensor):
    def read_state(self):
        # SIMULATION: Zu 5% ändert sich der Zustand zufällig
        if random.random() < 0.05:
            return random.choice([True, False])
        return self.last_state # Bleibt wie er ist

    def format_message(self, state):
        if state:
            return "Squishy wird gerade am Kopf gestreichelt."
        return "Das Streicheln hat aufgehört."

class OrientationSensor(BaseSensor):
    def read_state(self):
        # SIMULATION
        if random.random() < 0.02:
            return random.choice(["aufrecht", "auf der Seite", "kopfüber"])
        return self.last_state

    def format_message(self, state):
        return f"Squishys Position ist jetzt: {state}."