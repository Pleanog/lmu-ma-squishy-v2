import asyncio
import logging

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