import threading
import time
import random
import logging

class SensorManager:
    def __init__(self):
        # The "Shared Memory" of the device state
        self._state = {
            "brightness": "normal", # normal, low, high
            "shaken": False,
            "face_down": False,
            "battery_level": 100
        }
        self.running = False

    def get_metadata(self):
        """Returns the current snapshot of sensors for the API"""
        return self._state.copy()

    def start_simulation(self):
        """Starts the background thread to randomize values"""
        self.running = True
        threading.Thread(target=self._simulation_loop, daemon=True).start()
        logging.info("sensors   | 🟢 Simulation started (Updates every 10s)")

    def _simulation_loop(self):
        while self.running:
            time.sleep(10)
            
            self._state["shaken"] = random.choice([True, False, False, False]) # 25% chance
            self._state["face_down"] = random.choice([True, False, False]) # ~33% chance
            
            brightness_levels = ["low", "normal", "bright"]
            self._state["brightness"] = random.choice(brightness_levels)
            
            logging.info(f"sensors   | 🔄 State changed: {self._state}")