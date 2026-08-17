import logging
import time
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
                self.mpr121[pin].threshold = 8
                
            logger.info(f"MPR121 Touch Sensor '{self.name}' verbunden. Pins: {self.pins}. Empfindlichkeit ist auf MAX (2).")
        except Exception as e:
            logger.error(f"Fehler bei Touch-Sensor: {e}")
            self.mpr121 = None

        # Tracking für Gesten
        self.touch_history = []
        self.last_touch_time = 0
        self.touch_timeout = 0.4  # Zeitfenster für Streichel-Erkennung
        self._last_head_tap_ts = 0.0
        self._head_tap_window_seconds = 0.8

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
            if 0 in currently_touched and 2 in currently_touched:
                return "BOTH_SIDES_TOUCH"

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
            if self.touch_history and (current_time - self.last_touch_time > self.touch_timeout):
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

    def format_event(self, state):
        state_str = str(state)

        if state_str == "BOTH_SIDES_TOUCH":
            return {
                "sensor_id": "touch",
                "event": "squeeze",
                "value": "both_sides_touch",
                "intensity": None,
            }

        if not state_str.startswith("BERUEHRUNG_START_"):
            return None

        try:
            pin = int(state_str.split("_")[-1])
        except Exception:
            return None

        if pin == 8:
            return {
                "sensor_id": "touch",
                "event": "hush_touch",
                "value": f"pin={pin}",
                "intensity": None,
            }

        if pin == 4:
            now = time.time()
            if (now - self._last_head_tap_ts) <= self._head_tap_window_seconds:
                self._last_head_tap_ts = 0.0
                return {
                    "sensor_id": "touch",
                    "event": "tap_head",
                    "value": "head_double_tap",
                    "intensity": None,
                }
            self._last_head_tap_ts = now
            return None

        return {
            "sensor_id": "touch",
            "event": "press_head",
            "value": f"pin={pin}",
            "intensity": None,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n--- Starte TouchSensor Pin-Test ---")
    print("Gebe alle 2 Sekunden den Status aller Pins als Emojis aus (🟢 = Berührt, ⚪ = Frei).")
    print("Drücke STRG+C um den Test zu beenden.\n")

    # Initialisiere den Sensor
    sensor = TouchSensor("TouchSensor Test")

    try:
        while True:
            if sensor.mpr121 is not None:
                # Sammle die Emojis für jeden Pin
                visual_states = []
                for pin in sensor.pins:
                    is_touched = sensor.mpr121[pin].value
                    emoji = "🟢" if is_touched else "⚪"
                    
                    # Format z.B. "0:⚪" oder "4:🟢"
                    visual_states.append(f"{pin}:{emoji}")
                
                # Verbinde alles zu einem schönen, lesbaren String
                output_str = "  ".join(visual_states)
                
                # Aktuelle Uhrzeit formatieren
                current_time_str = time.strftime('%H:%M:%S')
                print(f"[{current_time_str}] {output_str}")
            else:
                print("Fehler: MPR121 Sensor nicht initialisiert oder nicht gefunden.")
            
            # 2 Sekunden warten
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nTest beendet. Tschüss!")