import logging
import time
from .base_sensor import BaseSensor

logger = logging.getLogger(__name__)

class TouchSensor(BaseSensor):
    # Standardmäßig überwachen wir jetzt ALLE Pins von 0 bis 11
    def __init__(self, name: str, pins=list(range(12))):
        super().__init__(name)
        self.pins = pins
        
        # --- NEU: ZUORDNUNG DER PINS (MAPPING) ---
        # Hier definieren wir, was welcher Pin bedeutet. 
        # (Die Farben sind nur für dich als Doku-Notiz)
        self.pin_mapping = {
            0: "rechte Seite (rot)",   # rot
            2: "linke Seite (blau)",    # blau
            4: "Kopf (gelb)",           # gelb
            8: "Front (grün)",          # grün
            11: "Misc (orange)"           # orange
        }
        
        # I2C Initialisierung
        try:
            import board
            import busio
            import adafruit_mpr121
            i2c = busio.I2C(board.SCL, board.SDA)
            self.mpr121 = adafruit_mpr121.MPR121(i2c)
            
            # --- EMPFINDLICHKEIT NOCHMALS ERHÖHT ---
            # Wir gehen mit dem Schwellenwert auf 2 (Standard ist 12!).
            # Das ist extrem empfindlich und sollte selbst schwache Signale 
            # über das Leitgarn zuverlässig erkennen.
            for pin in self.pins:
                self.mpr121[pin].threshold = 2
                
            logger.info(f"MPR121 Touch Sensor '{self.name}' verbunden. Pins: {self.pins}. Empfindlichkeit ist auf MAX (2).")
        except Exception as e:
            logger.error(f"Fehler bei Touch-Sensor: {e}")
            self.mpr121 = None

        # Tracking für Gesten
        self.touch_history = []
        self.last_touch_time = 0
        self.gesture_timeout = 0.4  # Zeitfenster für Streichel-Erkennung

    def get_location_name(self, pin):
        # Gibt "Kopf", "Front" etc. zurück. 
        # Wenn der Pin nicht im Dictionary steht (z.B. 1, 3, 5), gibt es "Pin 1" etc. aus.
        return self.pin_mapping.get(pin, f"Pin {pin}")

    def read_state(self):
        if self.mpr121 is None:
            return self.last_state

        # Welche Pins werden *jetzt* berührt?
        currently_touched = [p for p in self.pins if self.mpr121[p].value]
        current_time = time.time()

        if currently_touched:
            is_first_touch = len(self.touch_history) == 0
            self.last_touch_time = current_time
            
            # Pins zur Historie hinzufügen
            for p in currently_touched:
                if not self.touch_history or self.touch_history[-1] != p:
                    self.touch_history.append(p)
            
            if is_first_touch:
                # --- NEU: DYNAMISCHER STATUS ---
                # Wir hängen die Pin-Nummer einfach direkt an den Status an!
                # z.B. "BERUEHRUNG_START_4"
                first_pin = currently_touched[0]
                return f"BERUEHRUNG_START_{first_pin}"

            return "TOUCHING"

        else:
            if self.touch_history and (current_time - self.last_touch_time > self.gesture_timeout):
                history = self.touch_history
                self.touch_history = [] 
                
                unique_pins = list(dict.fromkeys(history))
                
                if len(unique_pins) >= 2:
                    # Wenn über mehrere Zonen gestreichelt wurde, 
                    # speichern wir Start und Ende in den Status.
                    # z.B. "STREICHELN_4_0" (Kopf zur rechten Seite)
                    start_pin = unique_pins[0]
                    end_pin = unique_pins[-1]
                    return f"STREICHELN_{start_pin}_{end_pin}"
                else:
                    return "BERUEHRUNG_ENDE"
            
            if not self.touch_history:
                return "IDLE"

        return self.last_state

    def format_message(self, state):
        # Wichtig: Nichts tun bei stummen Events (None zurückgeben)
        if state is None or state in ["TOUCHING", "IDLE", "BERUEHRUNG_ENDE"]:
            return None
            
        # Wir zerlegen den dynamischen String wieder
        if state.startswith("BERUEHRUNG_START_"):
            # Holt die Zahl am Ende aus "BERUEHRUNG_START_4"
            pin = int(state.split("_")[-1]) 
            ort = self.get_location_name(pin)
            return f"Jemand hat gerade angefangen, Squishys {ort} zu berühren."
            
        elif state.startswith("STREICHELN_"):
            # Holt Start und Ende aus "STREICHELN_4_0"
            parts = state.split("_")
            pin_start = int(parts[1])
            pin_end = int(parts[2])
            
            ort_start = self.get_location_name(pin_start)
            ort_end = self.get_location_name(pin_end)
            
            return f"Squishy wurde sanft von [{ort_start}] nach [{ort_end}] gestreichelt."
            
        return None