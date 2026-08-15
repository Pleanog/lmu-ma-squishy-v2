import logging
import asyncio
from .base_actuator import BaseActuator

logger = logging.getLogger(__name__)

class LEDActuator(BaseActuator):
    def __init__(self, name: str):
        super().__init__(name)
        self.current_state = False
        logger.info(f"🟢 [LED MOCK] Initialisiert für: {self.name}")

    async def execute(self, command: dict):
        """Mockt die LED-Steuerung durch einfache Log-Ausgaben."""
        color = command.get("color", "unknown")
        duration = command.get("duration", 1) # Default to 1 second if not provided
        
        logger.info(f"💡 [LED MOCK] Schalte auf Farbe: {color} für {duration} Sekunden...")
        self.current_state = True
        
        if duration > 0:
            await asyncio.sleep(duration)
            logger.info(f"💡 [LED MOCK] LED ({color}) wieder aus.")
            
        self.current_state = False