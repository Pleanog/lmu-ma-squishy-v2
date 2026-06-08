import asyncio
import logging
import os
from hardware.sounds.sound_effects import SOUND_EFFECTS

logger = logging.getLogger(__name__)

class BaseActuator:
    def __init__(self, name: str):
        self.name = name
        self.queue = asyncio.Queue()
        self.worker_task = None

    async def start(self):
        """Starte den Hintergrund-Arbeiter für diesen Aktor."""
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"⚙️ Actuator Worker gestartet: {self.name}")

    async def stop(self):
        """Stoppt den Arbeiter sauber."""
        if self.worker_task:
            self.queue.put_nowait(None) # Abbruch-Signal
            await self.worker_task

    def send_command(self, command: dict):
        """Wirft einen Befehl in die Warteschlange (Blockiert nicht!)."""
        self.queue.put_nowait(command)

    async def _worker_loop(self):
        """Die Schleife, die Befehle nacheinander abarbeitet."""
        while True:
            command = await self.queue.get()
            if command is None: # Beenden
                break
            
            try:
                await self.execute(command)
            except Exception as e:
                logger.error(f"Fehler im Aktor {self.name}: {e}")
            finally:
                self.queue.task_done()

    async def execute(self, command: dict):
        """MUSS von der spezifischen Hardware überschrieben werden."""
        raise NotImplementedError("Subklassen müssen execute() implementieren")


# --- SIMULIERTE AKTOREN (Später durch echten Code ersetzen) ---

class LEDActuator(BaseActuator):
    async def execute(self, command: dict):
        color = command.get("color", "white")
        duration = command.get("duration", 2)
        logger.info(f"💡 [LED] Leuchte {color} für {duration} Sekunden...")
        await asyncio.sleep(duration)
        logger.info(f"💡 [LED] Aus.")

class MotorActuator(BaseActuator):
    async def execute(self, command: dict):
        pattern = command.get("pattern", "buzz")
        logger.info(f"📳 [MOTOR] Vibriere Muster '{pattern}'...")
        await asyncio.sleep(1) # Simuliere Vibrationsdauer
        logger.info(f"📳 [MOTOR] Aus.")

class SoundActuator(BaseActuator):
    async def execute(self, command: dict):
        logger.info(f"🔊 [SOUND] Befehl erhalten: {command}")
        sound_type = command.get("sound_type")
        filepath = SOUND_EFFECTS.get(sound_type)
        if not filepath:
            logger.warning(f"Sound '{sound_type}' nicht gefunden")
            return
        logger.info(f"🎵 Spiele Sound: {sound_type}")
        process = await asyncio.create_subprocess_exec(
            "aplay",
            "-D",
            "default:CARD=sndrpihifiberry",
            filepath,
        )
        await process.wait()
        logger.info(f"🎵 Sound beendet: {sound_type}")
    






async def main():

    led = LEDActuator("LED")
    motor = MotorActuator("Motor")
    sound_effects = SoundActuator("Sound_Effects")

    # Worker starten
    await led.start()
    await motor.start()
    await sound_effects.start()

    print("\n=== Teste LED ===")
    led.send_command({
        "color": "green",
        "duration": 2
    })

    print("\n=== Teste Motor ===")
    motor.send_command({
        "pattern": "buzz"
    })

    print("\n=== Teste Sound ===")
    # loop over all sound effects for testing
    for effect in SOUND_EFFECTS.keys():
        logger.info(f"Teste Sound Effect: {effect}")
        sound_effects.send_command({
            "sound_type": effect
        })
        await asyncio.sleep(1) # Warte kurz zwischen den Sounds

    # Warten bis LED/Motor fertig sind
    await asyncio.sleep(5)

    # Worker sauber beenden
    await led.stop()
    await motor.stop()
    await sound_effects.stop()
    print("\n✅ Alle Tests abgeschlossen")


if __name__ == "__main__":
    asyncio.run(main())