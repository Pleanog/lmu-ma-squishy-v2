import asyncio
import logging
from typing import Callable
from hardware.base_actuator import LEDActuator, MotorActuator, SoundActuator
from hardware.base_sensor import TouchSensor, OrientationSensor

logger = logging.getLogger(__name__)

class HardwareHandler:
    def __init__(self, on_sensor_update_callback: Callable[[str], None]):
        self.on_sensor_update = on_sensor_update_callback
        
        # Initialisiere die Aktoren
        self.actuators = {
            "set_led_color": LEDActuator("LED_Ring"),
            "vibrate": MotorActuator("Vibration_Motor"),
            "play_sound_effect": SoundActuator("Sound_Effects"),
        }
        
        # Initialisiere die Sensoren
        self.sensors = [
            TouchSensor("Touch"),
            OrientationSensor("Gyro")
        ]
        
        self.monitor_task = None

    async def start(self):
        await asyncio.gather(
            *(actuator.start() for actuator in self.actuators.values())
        )
        
        self.monitor_task = asyncio.create_task(self._sensor_monitor_loop())
        logger.info("🤖 Hardware Handler gestartet.")

    async def stop(self):
        """Stoppt alles sauber."""
        await asyncio.gather(
            *(actuator.stop() for actuator in self.actuators.values())
        )
        if self.monitor_task:
            self.monitor_task.cancel()

    async def handle_tool_call(
        self,
        tool_name: str,
        args: dict,
        suggested_action: str = ""
    ):
        if suggested_action in ("simulate", "visualize"):
            logger.debug(
                f"Suggested_action='{suggested_action}': "
                f"Simuliere Tool Call '{tool_name}'"
            )
            return

        logger.info(
            f"Führe Tool aus: {tool_name} "
            f"(Aktion: {suggested_action}) "
            f"und args: {args}"
        )

        actuator = self.actuators.get(tool_name)

        if actuator:
            actuator.send_command(args)
        else:
            logger.warning(
                f"Unbekanntes Tool für Hardware: {tool_name}"
            )

    async def _sensor_monitor_loop(self):
        """Pollt die Sensoren kontinuierlich im Hintergrund."""
        try:
            while True:
                updates = []
                for sensor in self.sensors:
                    msg = sensor.get_update_if_changed()
                    if msg:
                        updates.append(msg)
                
                if updates:
                    # Fasse alle gleichzeitigen Änderungen in einen Satz zusammen
                    combined_message = "[System-Sensorik] " + " ".join(updates)
                    # Sende es an main.py zurück
                    if asyncio.iscoroutinefunction(self.on_sensor_update):
                        await self.on_sensor_update(combined_message)
                    else:
                        self.on_sensor_update(combined_message)
                        
                await asyncio.sleep(0.5) # Prüfe 2x pro Sekunde
        except asyncio.CancelledError:
            logger.debug("Sensor monitor loop beendet.")