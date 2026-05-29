import asyncio
import logging
from typing import Callable
from hardware.base_actuator import LEDActuator, MotorActuator
from hardware.base_sensor import TouchSensor, OrientationSensor

logger = logging.getLogger(__name__)

class HardwareHandler:
    def __init__(self, on_sensor_update_callback: Callable[[str], None]):
        self.on_sensor_update = on_sensor_update_callback
        
        # Initialisiere die Aktoren
        self.leds = LEDActuator("LED_Ring")
        self.motor = MotorActuator("Vibration_Motor")
        
        # Initialisiere die Sensoren
        self.sensors = [
            TouchSensor("Touch"),
            OrientationSensor("Gyro")
        ]
        
        self.monitor_task = None

    async def start(self):
        """Startet alle Aktor-Worker und das Sensor-Monitoring."""
        await self.leds.start()
        await self.motor.start()
        
        self.monitor_task = asyncio.create_task(self._sensor_monitor_loop())
        logger.info("🤖 Hardware Handler gestartet.")

    async def stop(self):
        """Stoppt alles sauber."""
        await self.leds.stop()
        await self.motor.stop()
        if self.monitor_task:
            self.monitor_task.cancel()

    def handle_tool_call(self, tool_name: str, args: dict, suggested_action: str = ""):
        """Verteilt einkommende KI-Befehle an den richtigen Aktor."""
        
        if suggested_action == "simulate" or suggested_action == "visualize":
            logger.debug(f"Suggested_action='{suggested_action}': Simuliere Tool Call '{tool_name}' mit args {args} (kein physischer Effekt).")
            return

        logger.info(f"Führe Tool aus: {tool_name} (Aktion: {suggested_action})")

        if tool_name == "set_led_color":
            self.leds.send_command(args)
        elif tool_name == "vibrate":
            self.motor.send_command(args)
        elif tool_name == "Task-12": # Aus deinen Logs: Gemini nutzt manchmal Task-12
            logger.info(f"Spezial-Task-12 empfangen mit args: {args}")
            # Leite es je nach Argument an LED oder Motor weiter
            if "color" in args:
                self.leds.send_command(args)
            elif "pattern" in args or "sound_type" in args:
                self.motor.send_command(args)
        else:
            logger.warning(f"Unbekanntes Tool für Hardware: {tool_name}")

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