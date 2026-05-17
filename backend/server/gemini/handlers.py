# FILE: app/gemini/handlers.py

import logging
from datetime import datetime
from typing import Optional
from models.events import AudioOutputEvent, AudioInterruptEvent
from websocket.manager import WebSocketManager 
# Importiere WebSocketClient, wenn du direkt mit dem Client-Objekt interagieren möchtest
from websocket.client import WebSocketClient # Füge diesen Import hinzu

logger = logging.getLogger(__name__)

def create_gemini_audio_output_handler(ws_manager: WebSocketManager):
    """
    Erstellt einen Callback, der rohe Audio-Bytes empfängt
    und sie in ein AudioOutputEvent verpackt, um es an den WebSocketManager zu senden.
    """
    async def audio_output_handler(audio_chunk: bytes):
        # ANPASSUNG HIER: Verwende get_active_controller() oder get_client_by_id()
        active_client: Optional[WebSocketClient] = ws_manager.get_active_controller() 
        # ws_manager.get_active_controller() sollte das WebSocketClient-Objekt zurückgeben

        if active_client: 
            audio_event = AudioOutputEvent(data=audio_chunk, timestamp=datetime.utcnow())
            # Sende das Event direkt an den Client, nicht an den Manager,
            # da der Manager bereits den Client gefunden hat.
            await active_client.send_event(audio_event) 
            logger.debug(f"Sent AudioOutputEvent ({len(audio_chunk)} bytes) to active controller {active_client.client_id}.")
        else:
            logger.debug("No active controller found to send audio to.")
    return audio_output_handler

def create_gemini_audio_interrupt_handler(ws_manager: WebSocketManager):
    """
    Erstellt einen Callback, der ein AudioInterruptEvent an den WebSocketManager sendet.
    """
    async def audio_interrupt_handler():
        # ANPASSUNG HIER: Verwende get_active_controller()
        active_client: Optional[WebSocketClient] = ws_manager.get_active_controller()

        if active_client:
            interrupt_event = AudioInterruptEvent(message="AI audio interrupted.", timestamp=datetime.utcnow())
            await active_client.send_event(interrupt_event)
            logger.debug(f"Sent AudioInterruptEvent to active controller {active_client.client_id}.")
        else:
            logger.debug("No active controller found to send audio interrupt to.")
    return audio_interrupt_handler