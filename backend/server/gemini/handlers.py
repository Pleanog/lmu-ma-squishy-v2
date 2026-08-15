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
        active_client: Optional[WebSocketClient] = ws_manager.resolve_audio_output_client()

        if active_client: 
            audio_event = AudioOutputEvent(data=audio_chunk, timestamp=datetime.utcnow())
            await active_client.send_event(audio_event) 
            logger.debug(f"Sent AudioOutputEvent ({len(audio_chunk)} bytes) to client {active_client.client_id}.")
        else:
            logger.debug("No active controller found to send audio to.")
    return audio_output_handler

def create_gemini_audio_interrupt_handler(ws_manager: WebSocketManager):
    """
    Erstellt einen Callback, der ein AudioInterruptEvent an den WebSocketManager sendet.
    """
    async def audio_interrupt_handler():
        active_client: Optional[WebSocketClient] = ws_manager.resolve_audio_output_client()

        if active_client:
            interrupt_event = AudioInterruptEvent(message="AI audio interrupted.", timestamp=datetime.utcnow())
            await active_client.send_event(interrupt_event)
            logger.debug(f"Sent AudioInterruptEvent to active controller {active_client.client_id}.")
        else:
            logger.debug("No active controller found to send audio interrupt to.")
    return audio_interrupt_handler