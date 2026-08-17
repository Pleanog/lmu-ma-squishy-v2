# FILE: app/gemini/handlers.py

import logging
from datetime import datetime
from typing import Callable, Optional

from models.events import AudioOutputEvent, AudioInterruptEvent
from websocket.manager import WebSocketManager 
from models.client_state import ClientCapability, ClientType

logger = logging.getLogger(__name__)

def create_gemini_audio_output_handler(
    ws_manager: WebSocketManager,
    should_emit_audio: Optional[Callable[[], bool]] = None,
):
    """
    Erstellt einen Callback, der rohe Audio-Bytes empfängt
    und sie ausschließlich an Frontend-Clients mit AUDIO_OUTPUT capability sendet.
    """
    async def audio_output_handler(audio_chunk: bytes):
        if should_emit_audio is not None and not should_emit_audio():
            return

        audio_event = AudioOutputEvent(data=audio_chunk, timestamp=datetime.utcnow())
        sent_count = 0

        for client in ws_manager.active_clients.values():
            if not client.state:
                continue
            if client.state.client_type != ClientType.FRONTEND:
                continue
            if ClientCapability.AUDIO_OUTPUT not in client.state.capabilities:
                continue
            await client.send_event(audio_event)
            sent_count += 1

        if sent_count == 0:
            logger.debug("No eligible frontend client available for audio output.")
    return audio_output_handler

def create_gemini_audio_interrupt_handler(ws_manager: WebSocketManager):
    """
    Erstellt einen Callback, der ein AudioInterruptEvent an den WebSocketManager sendet.
    """
    async def audio_interrupt_handler():
        interrupt_event = AudioInterruptEvent(message="AI audio interrupted.", timestamp=datetime.utcnow())
        sent_count = 0

        for client in ws_manager.active_clients.values():
            if not client.state:
                continue
            if client.state.client_type != ClientType.FRONTEND:
                continue
            if ClientCapability.AUDIO_OUTPUT not in client.state.capabilities:
                continue
            await client.send_event(interrupt_event)
            sent_count += 1

        if sent_count == 0:
            logger.debug("No eligible frontend client available for audio interrupt.")
    return audio_interrupt_handler