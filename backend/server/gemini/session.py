# FILE: app/gemini/session.py

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from uuid import uuid4
from datetime import datetime # Importiere datetime

from google.genai import types
from models.client_state import ClientCapability
from gemini_live import GeminiLive

from config import settings
from models.events import (
    ErrorEvent, TranscriptEvent, AudioOutputEvent, AudioInterruptEvent,
    ToolCallEvent, AIResponseEvent, OutgoingEventType, SystemMessageEvent
)
from websocket.manager import WebSocketManager
from tools.dispatcher import ToolDispatcher

# Behalte create_gemini_audio_output_handler und create_gemini_audio_interrupt_handler
# oder definiere die Callbacks direkt hier, wie im alten main.py
# Wenn sie in gemini.handlers sind, stelle sicher, dass sie AudioOutputEvent senden.
# Für diesen Fix passen wir create_gemini_audio_output_handler an, um AudioOutputEvent zu verwenden.
from gemini.handlers import create_gemini_audio_output_handler, create_gemini_audio_interrupt_handler


logger = logging.getLogger(__name__)

class GeminiSessionManager:
    """
    Manages a single, shared Gemini Live session for the entire application.
    Handles input queues (audio, text, video) and routes Gemini's output
    (transcripts, audio, tool calls, AI responses) to the WebSocketManager.
    """
    def __init__(self, ws_manager: 'WebSocketManager', tool_dispatcher: 'ToolDispatcher'):
        self.ws_manager = ws_manager
        self.tool_dispatcher = tool_dispatcher

        self.audio_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.text_input_queue: asyncio.Queue[str] = asyncio.Queue()
        self.video_input_queue: asyncio.Queue[bytes] = asyncio.Queue() # For image chunks
        self.tool_response_queue: asyncio.Queue[Tuple[str, str, Dict[str, Any]]] = asyncio.Queue()

        self._gemini_live_client: Optional[GeminiLive] = None
        self._gemini_session_task: Optional[asyncio.Task] = None
        self._tool_response_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

        self._last_ai_response_id: Optional[str] = None

        logger.info("GeminiSessionManager initialized.")

    async def initialize_gemini_client(self):
        """Initializes the GeminiLive client with tools and callbacks."""
        if self._gemini_live_client:
            logger.warning("GeminiLive client already initialized.")
            return

        tool_mapping: Dict[str, Callable[..., Any]] = {}
        # Iterate over each Tool object, then over its function_declarations
        for tool_schema in self.tool_dispatcher.get_all_tool_schemas():
            for func_declaration in tool_schema.function_declarations:
                tool_mapping[func_declaration.name] = self._tool_call_wrapper

        self._gemini_live_client = GeminiLive(
            api_key=settings.GEMINI_API_KEY,
            model=settings.MODEL,
            input_sample_rate=settings.AUDIO_SAMPLE_RATE,
            tools=self.tool_dispatcher.get_all_tool_schemas(),
            tool_mapping=tool_mapping
        )
        logger.info("GeminiLive client initialized with tool mapping.")

    async def _tool_call_wrapper(self, **kwargs: Any) -> types.FunctionResponse:
        """
        A wrapper function that GeminiLive calls for tool calls.
        This puts the tool call on a queue for the ToolDispatcher to handle,
        and returns a placeholder response to Gemini immediately.
        The actual function response will be sent back to Gemini later
        when a client provides it.
        """
        tool_name = asyncio.current_task().get_name() # GeminiLive sets task name to tool name
        tool_call_id = str(uuid4()) # Generate a unique ID for this specific tool call

        logger.info(f"Gemini requested tool call: {tool_name} with args: {kwargs}. Assigned ID: {tool_call_id}")

        tool_call_event = ToolCallEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            args=kwargs,
            # Clients will determine their action based on capabilities
            suggested_action="execute" if self.ws_manager.get_active_controller() and self.ws_manager.get_active_controller().state and ClientCapability.TOOL_EXECUTION in self.ws_manager.get_active_controller().state.capabilities else "visualize"
        )
        await self.tool_dispatcher.dispatch_tool_call(tool_call_event)

        # GeminiLive expects a FunctionResponse immediately.
        # We'll return a placeholder and send the real response later from the client.
        # The 'result' key is required, and we add a 'status' for internal tracking.
        return types.FunctionResponse(
            id=tool_call_id,
            name=tool_name,
            response={"status": "dispatched", "message": "Tool call dispatched to clients, awaiting response."}
        )

    async def _process_tool_responses(self):
        """Continuously processes tool responses coming from clients."""
        while self._is_running:
            try:
                tool_call_id, tool_name, result = await self.tool_response_queue.get()
                if self._gemini_live_client:
                    logger.info(f"Sending tool response for {tool_name}/{tool_call_id} to Gemini: {result}")
                    function_response = types.FunctionResponse(
                        id=tool_call_id,
                        name=tool_name,
                        response=result
                    )
                    await self._gemini_live_client.send_tool_response(function_responses=[function_response])
                else:
                    logger.warning("GeminiLive client not initialized, cannot send tool response.")
                self.tool_response_queue.task_done()
            except asyncio.CancelledError:
                logger.info("Tool response processing task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error processing tool response: {e}", exc_info=True)

    async def start_session(self):
        """Starts the Gemini Live session and all related tasks."""
        if self._is_running:
            logger.warning("Gemini session is already running.")
            return

        if not self._gemini_live_client:
            await self.initialize_gemini_client()
        if not self._gemini_live_client:
            logger.error("Failed to initialize GeminiLive client, cannot start session.")
            return

        self._is_running = True
        logger.info("Starting Gemini session tasks.")

        self._tool_response_task = asyncio.create_task(self._process_tool_responses())

        # HIER DIE ANPASSUNG FÜR AUDIO-CALLBACKS:
        # Die create_gemini_audio_output_handler/interrupt_handler müssen
        # jetzt ein AudioOutputEvent an den ws_manager senden.
        audio_output_callback = create_gemini_audio_output_handler(self.ws_manager)
        audio_interrupt_callback = create_gemini_audio_interrupt_handler(self.ws_manager)

        self._gemini_session_task = asyncio.create_task(
            self._run_gemini_session(audio_output_callback, audio_interrupt_callback)
        )
        await self.ws_manager.broadcast(SystemMessageEvent(message="Gemini session started."))


    async def _run_gemini_session(self, audio_output_cb: Callable, audio_interrupt_cb: Optional[Callable]): # Callbacks sind jetzt Parameter
        try:
            async for response_event_from_gemini_live in self._gemini_live_client.start_session( # Umbenannt für Klarheit
                audio_input_queue=self.audio_input_queue,
                video_input_queue=self.video_input_queue,
                text_input_queue=self.text_input_queue,
                audio_output_callback=audio_output_cb,       # Hier werden die Callbacks übergeben
                audio_interrupt_callback=audio_interrupt_cb, # Hier werden die Callbacks übergeben
            ):

                if not response_event_from_gemini_live:
                    continue

                logger.info(f"RESPONSE TYPE from gemini_live.py: {type(response_event_from_gemini_live)}")
                logger.debug(f"FULL RESPONSE from gemini_live.py: {response_event_from_gemini_live}")

                # Die event_queue in gemini_live.py sendet DICTS, nicht die direkten genai.types.Responses.
                # Wir müssen diese DICTS jetzt parsen und in unsere Pydantic Events umwandeln.
                
                response_type = response_event_from_gemini_live.get("type")

                if response_type == "gemini":
                    # Dies ist eine Text-Transkription aus Gemini's output
                    text = response_event_from_gemini_live.get("text")
                    if text:
                        ai_response_event = AIResponseEvent(
                            text=text,
                            timestamp=datetime.utcnow()
                        )
                        await self.ws_manager.broadcast(ai_response_event)
                        logger.info(f"AI Response (Text): {text}")
                
                elif response_type == "user":
                    # Dies ist eine Text-Transkription aus Gemini's input (des Nutzers)
                    text = response_event_from_gemini_live.get("text")
                    if text:
                        transcript_event = TranscriptEvent(
                            text=text,
                            is_final=True, # gemini_live.py sendet finale Transkriptionen
                            timestamp=datetime.utcnow()
                        )
                        await self.ws_manager.broadcast(transcript_event)
                        logger.info(f"User Transcript: {text}")

                elif response_type == "tool_call":
                    # Tool calls werden im _tool_call_wrapper bereits gehandhabt,
                    # aber gemini_live.py kann hier auch ein vereinfachtes dict senden.
                    # Wir sollten sicherstellen, dass wir hier keine doppelten Events erzeugen,
                    # oder dass dieses Event nur zur Info ist.
                    # Die primäre ToolCallEvent-Erzeugung findet in _tool_call_wrapper statt.
                    logger.debug(f"Received tool_call notification from gemini_live.py event_queue: {response_event_from_gemini_live}")
                    # Wenn du dieses Event an Clients senden möchtest, müsstest du es
                    # in ein ToolCallEvent (Pydantic) umwandeln und broadcasten.
                    # Das _tool_call_wrapper kümmert sich bereits darum, daher hier nur Debugging.
                
                elif response_type == "turn_complete":
                    logger.debug("Gemini turn complete.")
                    # Optional: Ein Event senden, wenn ein Turn abgeschlossen ist
                    # await self.ws_manager.broadcast(SystemMessageEvent(message="Gemini turn completed.", timestamp=datetime.utcnow()))
                
                elif response_type == "interrupted":
                    logger.debug("Gemini interrupted.")
                    # AudioInterruptEvent wird vom audio_interrupt_cb gesendet,
                    # daher hier keine weitere Aktion nötig, wenn der Callback verwendet wird.
                
                elif response_type == "error":
                    error_msg = response_event_from_gemini_live.get("error", "Unknown error from Gemini Live.")
                    logger.error(f"Error from Gemini Live event_queue: {error_msg}")
                    await self.ws_manager.broadcast(ErrorEvent(message=f"Gemini Live Error: {error_msg}", timestamp=datetime.utcnow()))
                
                else:
                    logger.warning(f"Unhandled event type from gemini_live.py event_queue: {response_type}")
                    logger.debug(f"Full unhandled event: {response_event_from_gemini_live}")

        except Exception as e:
            logger.error(f"Error in Gemini session: {e}", exc_info=True)

    async def stop_session(self):
        """Stops the Gemini Live session and associated tasks."""
        if not self._is_running:
            logger.info("Gemini session is not running.")
            return

        logger.info("Stopping Gemini session tasks.")
        self._is_running = False

        if self._gemini_session_task:
            self._gemini_session_task.cancel()
            try:
                await self._gemini_session_task
            except asyncio.CancelledError:
                pass

        if self._tool_response_task:
            self._tool_response_task.cancel()
            try:
                await self._tool_response_task
            except asyncio.CancelledError:
                pass

        # Clear queues
        while not self.audio_input_queue.empty():
            await self.audio_input_queue.get()
            self.audio_input_queue.task_done()
        while not self.text_input_queue.empty():
            await self.text_input_queue.get()
            self.text_input_queue.task_done()
        while not self.video_input_queue.empty():
            await self.video_input_queue.get()
            self.video_input_queue.task_done()
        while not self.tool_response_queue.empty():
            await self.tool_response_queue.get()
            self.tool_response_queue.task_done()

        logger.info("GeminiSessionManager stopped.")
        await self.ws_manager.broadcast(SystemMessageEvent(message="Gemini session has been stopped."))