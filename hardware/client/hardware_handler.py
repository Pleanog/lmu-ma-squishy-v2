import asyncio
import logging
import time
from typing import Any, Callable, Optional
from hardware.base_actuator import MotorActuator, SoundActuator
from hardware.led_actuator import LEDActuator
from hardware.touch_sensor import TouchSensor
from hardware.gyro_sensor import OrientationSensor
from hardware.flex_sensor import FlexSensor


logger = logging.getLogger(__name__)

class HardwareHandler:
    def __init__(self, on_sensor_update_callback: Callable[[str, str, Any, Optional[str]], None]):
        self.on_sensor_update = on_sensor_update_callback
        self._sensor_event_debounce_seconds = 2.0
        self._last_sensor_event_ts = 0.0
        
        # Initialisiere die Aktoren
        self.actuators = {
            "set_led_color": LEDActuator("LED_Ring"),
            "vibrate": MotorActuator("Vibration_Motor"),
            "play_sound_effect": SoundActuator("Sound_Effects"),
        }
        
        # Initialisiere die Sensoren
        self.sensors = [
            TouchSensor("Touch"),
            OrientationSensor("Gyro"),
            FlexSensor("Flex")
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
        """Pollt die Sensoren kontinuierlich und sendet deren Events an das Backend."""
        try:
            while True:
                for sensor in self.sensors:
                    event_payload = sensor.get_event_if_changed()
                    if not event_payload:
                        continue

                    sensor_id = event_payload.get("sensor_id")
                    event_type = event_payload.get("event")
                    value = event_payload.get("value")
                    intensity = event_payload.get("intensity")

                    if not sensor_id or not event_type:
                        continue

                    # await self._emit_sensor_event(
                    #     sensor_id=str(sensor_id),
                    #     event_type=str(event_type),
                    #     value=value,
                    #     intensity=intensity,
                    #     source=sensor.name,
                    # )

                await asyncio.sleep(0.5) # Prüfe 2x pro Sekunde
        except asyncio.CancelledError:
            logger.debug("Sensor monitor loop beendet.")

    async def _emit_sensor_event(self, sensor_id: str, event_type: str, value: Any, intensity: Optional[str], source: str):
        now = time.time()
        if (now - self._last_sensor_event_ts) < self._sensor_event_debounce_seconds:
            logger.debug(f"Skipping sensor event '{event_type}' from {source} due to global debounce window.")
            return

        self._last_sensor_event_ts = now
        logger.info(f"Sending sensor event '{event_type}' from {source} to backend.")
        if asyncio.iscoroutinefunction(self.on_sensor_update):
            await self.on_sensor_update(sensor_id, event_type, value, intensity)
        else:
            self.on_sensor_update(sensor_id, event_type, value, intensity)