import logging
import time
from .base_sensor import BaseSensor

logger = logging.getLogger(__name__)

class OrientationSensor(BaseSensor):
    def __init__(self, name: str):
        super().__init__(name)
       
        try:
            import board
            import busio
            import adafruit_mpu6050
            # Wir nutzen denselben I2C Bus wie der Touch Sensor!
            i2c = busio.I2C(board.SCL, board.SDA)
            self.mpu = adafruit_mpu6050.MPU6050(i2c)
            logger.info(f"MPU6050 Orientierungssensor '{self.name}' verbunden.")
        except Exception as e:
            logger.error(f"Fehler bei Orientierungssensor: {e}")
            self.mpu = None

        # Robustheits-Variablen
        self.debounce_time = 1.0  # Position muss 1.0 Sekunden stabil sein
        self.candidate_state = None
        self.candidate_start_time = 0
        self.current_stable_state = None

        # HIER KANNST DU DEINE EVENTS MAPPEN!
        # Die Achsen hängen davon ab, wie du den Sensor physisch ins Kuscheltier einbaust.
        # Du musst das beim Testen einmal ausprobieren und dann hier anpassen.
        self.mapping = {
            "+Z": "Squishy steht ganz normal aufrecht.",
            "-Z": "Squishy wurde auf den Kopf gestellt!",
            "+X": "Squishy liegt auf der rechten Seite.",
            "-X": "Squishy liegt auf der linken Seite.",
            "+Y": "Squishy liegt auf dem Rücken und schaut nach oben.",
            "-Y": "Squishy liegt auf dem Bauch mit dem Gesicht zum Boden."
        }

    def read_state(self):
        if self.mpu is None:
            return self.last_state

        try:
            # Versuche die Beschleunigung zu lesen
            ax, ay, az = self.mpu.acceleration
        except OSError as e:
            # Hängt den Fehler [Errno 121] ab! Ein kurzes Verbindungsproblem.
            logger.debug(f"I2C Wackelkontakt am MPU6050 ignoriert: {e}")
            return self.last_state # Gib den alten Status zurück, bis es wieder geht
        except Exception as e:
            logger.error(f"Unerwarteter Fehler am MPU6050: {e}")
            return self.last_state

        # Wenn das Lesen erfolgreich war, geht es hier normal weiter:
        axes = {'X': ax, 'Y': ay, 'Z': az}
        dominant_axis = max(axes, key=lambda k: abs(axes[k]))
        
        sign = "+" if axes[dominant_axis] > 0 else "-"
        raw_position = f"{sign}{dominant_axis}"

        current_time = time.time()

        if raw_position != self.candidate_state:
            self.candidate_state = raw_position
            self.candidate_start_time = current_time
        elif (current_time - self.candidate_start_time) > self.debounce_time:
            if self.current_stable_state != raw_position:
                self.current_stable_state = raw_position
                return raw_position

        return self.last_state

    def format_message(self, state):
        # Das Kürzel (z.B. "+Z") im Dictionary nachschlagen
        return self.mapping.get(state, f"Unbekannte Position: {state}")

    def format_event(self, state):
        state_str = str(state)
        if state_str == "+Z":
            return {
                "sensor_id": "gyro",
                "event": "drop_on_table",
                "value": state_str,
                "intensity": None,
            }
        if state_str == "+X":
            return {
                "sensor_id": "gyro",
                "event": "target_focus",
                "value": state_str,
                "intensity": None,
            }
        if state_str == "-X":
            return {
                "sensor_id": "gyro",
                "event": "horizontal_turn",
                "value": state_str,
                "intensity": None,
            }
        if state_str in {"+Y", "-Y"}:
            return {
                "sensor_id": "gyro",
                "event": "shake",
                "value": state_str,
                "intensity": None,
            }
        return None