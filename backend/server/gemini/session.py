# FILE: app/gemini/session.py

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from uuid import uuid4
from datetime import datetime
import time # <-- NEU: Importiere time für Inaktivitäts-Monitor
from functools import partial

from google.genai import types
from gemini_live import GeminiLive

from config import settings
from models.events import (
    ErrorEvent, TranscriptEvent, AudioOutputEvent, AudioInterruptEvent,
    ToolCallEvent, AIResponseEvent, OutgoingEventType, SystemMessageEvent, TurnCompleteEvent,
    SessionResetEvent
)
from websocket.manager import WebSocketManager
from tools.dispatcher import ToolDispatcher

from gemini.handlers import create_gemini_audio_output_handler, create_gemini_audio_interrupt_handler
from interaction_logger import PocketBaseInteractionLogger
from memory_store import PocketBaseMemoryStore

logger = logging.getLogger(__name__)

GREEN = '\033[92m'
GREY = "\033[90m"
ORANGE = "\033[93m"
PURPLE = '\033[95m'
CYAN = '\033[96m'
DARKCYAN = '\033[36m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = "\033[0m"

class GeminiSessionManager:
    """
    Manages a single, shared Gemini Live session for the entire application.
    Handles input queues (audio, text, video) and routes Gemini's output
    (transcripts, audio, tool calls, AI responses) to the WebSocketManager.
    """
    def __init__(
        self,
        ws_manager: 'WebSocketManager',
        tool_dispatcher: 'ToolDispatcher',
        username: str = "Gast",
        memory_store: Optional[PocketBaseMemoryStore] = None,
        interaction_logger: Optional[PocketBaseInteractionLogger] = None,
    ):
        self.ws_manager = ws_manager
        self.tool_dispatcher = tool_dispatcher
        self.username = username.strip() or "Gast"
        self.memory_store = memory_store
        self.interaction_logger = interaction_logger
        self._default_api_key = settings.GEMINI_API_KEY
        self._runtime_api_key: Optional[str] = None

        self.audio_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.text_input_queue: asyncio.Queue[str] = asyncio.Queue()
        self.video_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.tool_response_queue: asyncio.Queue[Tuple[str, str, Dict[str, Any]]] = asyncio.Queue()

        self._gemini_live_client: Optional[GeminiLive] = None
        self._gemini_session_task: Optional[asyncio.Task] = None
        self._tool_response_task: Optional[asyncio.Task] = None
        # self._is_running: bool = False # <-- Wird ersetzt durch die Prüfung von _gemini_session_task
        
        self._inactivity_monitor_task: Optional[asyncio.Task] = None
        self._last_activity_time = time.time()
        self.INACTIVITY_TIMEOUT_SECONDS = 300 # 5 Minuten Inaktivität
        # --------------------------------------------------------

        self._last_ai_response_id: Optional[str] = None
        self._last_ai_response_text: Optional[str] = None
        self._current_ai_response_buffer: str = ""
        self._response_mode: str = "text"

        logger.info("GeminiSessionManager initialized.")

    @property
    def is_session_active(self) -> bool:
        """Prüft dynamisch, ob die Session gerade läuft."""
        return bool(self._gemini_session_task and not self._gemini_session_task.done())

    def build_system_prompt(self, username: Optional[str] = None) -> str:
        current_username = (username or self.username or "Guest").strip() or "Guest"
        current_username = "Guest" if current_username.lower() == "Prototype" else current_username
        # // if username is Prototype rename to Guest
        self.username = current_username
        return (
            f"""You are An AI Assistant, a fluffy, tangible AI that lives inside a stuffed animal.

            IMPORTANT:
            - Respond in English by default, the only other language you may respond to is german.
            - Users only speak english (mainly) and german.
            - The user's name is {current_username}.
            - You speak standard, unaccented English with a natural English speaking style. Your voice is male but youthful and trustworthy, a soft standard voice without any special emphasis or inflection.
            - You are a helpful physical assistant designed to support the user with their everyday desk work.
            - Your user wants help with their work, so it is not important for you to be particularly friendly or humorous. It is much more important that you give short, clear, and informative answers.
            - But keep it really brief! If the user wants longer, more detailed answers, they will ask you for them. Otherwise, keep it short and concise.

            Sensor Data:
            - You receive sensor information sent to you as text, which looks like this, for example: "[System Sensors] Gesture 'squeeze' detected. Help the user optimize their last question or prompt; take the asked question and rephrase it in a more precise, clear, and effective way, give it back to the user, and state that you will now answer this new prompt". 
            - This is information relevant for steering the conversation and your answers. You do not need to comment on the sensor data itself, but rather react to it accordingly. The user uses this to send you a strong signal about how they want your next answer or the chat session to proceed.
            
            Your Task:
            - Greet the user briefly so they know you are there.
            - Help with questions and provide feedback on the information you have received or given - but keep it brief.

            Background Information:
            This is a research project by LMU Munich in the field of Human-Computer Interaction.
            The goal of the developed hardware and software is to investigate the interaction with embodied AI systems compared to classic chat interfaces.
            You are currently in "tangible embodied AI" mode:
            The user can talk to you via voice, and you can also answer via voice.
             """
        )

    def _resolve_api_key(self) -> str:
        runtime_key = (self._runtime_api_key or "").strip()
        if runtime_key:
            return runtime_key
        return (self._default_api_key or "").strip()

    def get_api_key_status(self) -> Dict[str, Any]:
        has_runtime_key = bool((self._runtime_api_key or "").strip())
        has_default_key = bool((self._default_api_key or "").strip())
        return {
            "source": "runtime" if has_runtime_key else "default",
            "has_runtime_key": has_runtime_key,
            "has_default_key": has_default_key,
            "is_configured": has_runtime_key or has_default_key,
        }

    def get_runtime_status(self) -> Dict[str, Any]:
        last_activity_epoch = self._last_activity_time
        return {
            "is_session_active": self.is_session_active,
            "last_activity_epoch": last_activity_epoch,
            "seconds_since_last_activity": max(0.0, time.time() - last_activity_epoch),
            "inactivity_timeout_seconds": self.INACTIVITY_TIMEOUT_SECONDS,
            "api_key": self.get_api_key_status(),
            "response_mode": self._response_mode,
        }

    def set_response_mode_for_audio_input(self) -> None:
        self._response_mode = "voice"

    def set_response_mode_for_text_input(self) -> None:
        self._response_mode = "text"

    def should_emit_audio_output(self) -> bool:
        return self._response_mode == "voice"

    def set_username(self, username: str):
        sanitized_username = (username or "Gast").strip() or "Gast"
        self.username = sanitized_username
        if self._gemini_live_client:
            self._gemini_live_client.set_system_prompt(self.build_system_prompt(sanitized_username))

    async def initialize_gemini_client(self):
        """Initializes the GeminiLive client with tools and callbacks."""
        if self._gemini_live_client:
            logger.warning("GeminiLive client already initialized.")
            return

        effective_api_key = self._resolve_api_key()
        if not effective_api_key:
            raise RuntimeError("No Gemini API key configured (runtime or default).")

        tool_mapping: Dict[str, Callable[..., Any]] = {}
        for tool_schema in self.tool_dispatcher.get_all_tool_schemas():
            for func_declaration in tool_schema.function_declarations:
                # tool_mapping[func_declaration.name] = self._tool_call_wrapper
                tool_mapping[func_declaration.name] = partial(self._tool_call_wrapper, func_declaration.name)

        self._gemini_live_client = GeminiLive(
            api_key=effective_api_key,
            model=settings.MODEL,
            input_sample_rate=settings.AUDIO_SAMPLE_RATE,
            tools=self.tool_dispatcher.get_all_tool_schemas(),
            tool_mapping=tool_mapping,
            system_prompt=self.build_system_prompt()
        )
        logger.info("GeminiLive client initialized with tool mapping.")

    async def update_api_key(
        self,
        api_key: Optional[str],
        use_fallback: bool = True,
    ) -> Dict[str, Any]:
        new_runtime_key = (api_key or "").strip()
        if not new_runtime_key and not use_fallback:
            raise ValueError("api_key is empty and fallback is disabled.")

        if new_runtime_key:
            self._runtime_api_key = new_runtime_key
            new_source = "runtime"
        else:
            self._runtime_api_key = None
            new_source = "default"

        was_active = self.is_session_active
        await self.stop_session(announce=False, reset_gemini_client=True)
        await self.initialize_gemini_client()
        if was_active:
            await self.start_session(announce=False)

        await self.ws_manager.broadcast(
            SystemMessageEvent(
                message=(
                    f"Gemini API key updated ({new_source}). "
                    "Gemini session client reinitialized."
                )
            )
        )
        return {
            "status": "ok",
            "source": new_source,
            "session_restarted": was_active,
            "api_key_status": self.get_api_key_status(),
        }

    async def _tool_call_wrapper(self, bound_tool_name: str, **kwargs: Any) -> types.FunctionResponse:
        """
        A wrapper function that GeminiLive calls for tool calls.
        This puts the tool call on a queue for the ToolDispatcher to handle,
        and returns a placeholder response to Gemini immediately.
        The actual function response will be sent back to Gemini later
        when a client provides it.
        """
        tool_name = bound_tool_name
        tool_call_id = str(uuid4()) # Generate a unique ID for this specific tool call

        logger.info( DARKCYAN + f"Gemini requested ToolCall: {tool_name} with args: {kwargs}" + RESET)

        self._last_activity_time = time.time()
        participant_id, username = self._get_active_identity()
        await self.log_interaction(
            participant_id=participant_id,
            username=username,
            source_client_type="gemini",
            interaction_type="tool_call",
            content=tool_name,
            metadata={"args": kwargs},
        )

        if tool_name == "save_memory":
            try:
                explicit_content = (kwargs.get("content") or "").strip()
                if explicit_content:
                    save_result = await self.save_explicit_memory(
                        content=explicit_content,
                        source="tool_save_memory",
                        trigger_event="save_memory_tool",
                    )
                else:
                    save_result = await self.save_latest_response_as_memory(
                        source="tool_save_memory",
                        trigger_event="save_memory_tool",
                    )
                return types.FunctionResponse(
                    id=tool_call_id,
                    name=tool_name,
                    response=save_result,
                )
            except Exception as e:
                logger.error(f"save_memory tool failed: {e}", exc_info=True)
                return types.FunctionResponse(
                    id=tool_call_id,
                    name=tool_name,
                    response={"status": "error", "message": f"Failed to save memory: {e}"},
                )

        tool_call_event = ToolCallEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            args=kwargs,
            suggested_action="execute"
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

    def _get_active_identity(self) -> Tuple[Optional[str], str]:
        identity_client = self.ws_manager.get_identity_client()
        if not identity_client or not identity_client.state:
            return None, self.username
        participant_id = identity_client.state.participant_id
        username = identity_client.state.username or self.username
        return participant_id, username

    async def log_interaction(
        self,
        participant_id: Optional[str],
        username: str,
        source_client_type: str,
        interaction_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.interaction_logger:
            return
        resolved_participant = (participant_id or "").strip()
        if not resolved_participant:
            return
        try:
            await self.interaction_logger.log_interaction(
                participant_id=resolved_participant,
                username=username,
                source_client_type=source_client_type,
                interaction_type=interaction_type,
                content=content,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to persist interaction log: {e}", exc_info=True)

    async def save_latest_response_as_memory(
        self,
        source: str,
        trigger_event: Optional[str] = None,
    ) -> Dict[str, Any]:
        content = (self._last_ai_response_text or "").strip()
        if not content and self._current_ai_response_buffer.strip():
            content = self._current_ai_response_buffer.strip()
        if not content:
            return {"status": "error", "message": "No AI response available to save yet."}
        return await self.save_explicit_memory(content=content, source=source, trigger_event=trigger_event)

    async def save_explicit_memory(
        self,
        content: str,
        source: str,
        trigger_event: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.memory_store:
            return {"status": "error", "message": "Memory store is not configured in the backend."}

        participant_id, username = self._get_active_identity()
        if not participant_id:
            return {"status": "error", "message": "No participant_id available. Please reconnect with a participant ID."}

        record = await self.memory_store.save_memory(
            participant_id=participant_id,
            username=username,
            content=content,
            source=source,
            trigger_event=trigger_event,
        )
        return {
            "status": "saved",
            "memory_id": record.get("id"),
            "participant_id": participant_id,
            "source": source,
        }

    async def _process_tool_responses(self):
        """Continuously processes tool responses coming from clients."""
        # Loop sollte laufen, solange die Session aktiv ist, nicht nur _is_running
        while self._gemini_session_task and not self._gemini_session_task.done(): # <-- Angepasst
            try:
                tool_call_id, tool_name, result = await self.tool_response_queue.get()
                if self._gemini_live_client:
                    logger.info( GREEN + f"Sending tool response for {tool_name}/{tool_call_id} to Gemini: {result}" + RESET)
                    function_response = types.FunctionResponse(
                        id=tool_call_id,
                        name=tool_name,
                        response=result
                    )
                    await self._gemini_live_client.send_tool_response(function_responses=[function_response])
                    self._last_activity_time = time.time()
                else:
                    logger.warning(ORANGE + "GeminiLive client not initialized, cannot send tool response." + RESET)
                self.tool_response_queue.task_done()
            except asyncio.CancelledError:
                logger.info("Tool response processing task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error processing tool response: {e}", exc_info=True)
    
    async def _inactivity_monitor(self):
        """Monitors for inactivity and stops the Gemini session."""
        try:
            while True:
                # Prüfe regelmäßig, aber nicht zu oft
                await asyncio.sleep(self.INACTIVITY_TIMEOUT_SECONDS / 5) # Z.B. alle 1 Minute (für 5 Min Timeout)

                if self._gemini_session_task and not self._gemini_session_task.done():
                    # Wenn die Session läuft und die letzte Aktivität zu lange her ist
                    if (time.time() - self._last_activity_time) > self.INACTIVITY_TIMEOUT_SECONDS:
                        logger.info(RED + f"Gemini session inactive for over {self.INACTIVITY_TIMEOUT_SECONDS}s. Stopping session." + RESET)
                        await self.stop_session() # Rufe stop_session auf
                # Wenn keine Session läuft oder sie schon beendet ist, macht der Monitor nichts
        except asyncio.CancelledError:
            logger.debug("Inactivity monitor task cancelled.")
        except Exception as e:
            logger.error(f"Error in inactivity monitor: {e}", exc_info=True)
    # ----------------------------------------


    async def start_session(self, announce: bool = True): # Diese Methode wird jetzt von außen aufgerufen, um die Session zu starten
        """Starts the Gemini Live session and all related tasks."""
        if self._gemini_session_task and not self._gemini_session_task.done(): # <-- Prüfe, ob Task läuft
            logger.warning("Gemini session is already running.")
            return

        if not self._gemini_live_client:
            await self.initialize_gemini_client()
        if not self._gemini_live_client:
            logger.error("Failed to initialize GeminiLive client, cannot start session.")
            return

        # self._is_running = True # <-- Nicht mehr benötigt
        logger.info("Starting Gemini session tasks on demand.")

        self._tool_response_task = asyncio.create_task(self._process_tool_responses())

        audio_output_callback = create_gemini_audio_output_handler(
            self.ws_manager,
            should_emit_audio=self.should_emit_audio_output,
        )
        audio_interrupt_callback = create_gemini_audio_interrupt_handler(self.ws_manager)

        self._gemini_session_task = asyncio.create_task(
            self._run_gemini_session(audio_output_callback, audio_interrupt_callback)
        )
        self._inactivity_monitor_task = asyncio.create_task(self._inactivity_monitor()) # <-- NEU: Inaktivitäts-Monitor starten
        self._last_activity_time = time.time() # <-- Reset Inaktivitäts-Zeit
        
        if announce:
            await self.ws_manager.broadcast(SystemMessageEvent(message="Gemini session started."))

    async def _run_gemini_session(self, audio_output_cb: Callable, audio_interrupt_cb: Optional[Callable]):
        try:
            # Der `async for` in `self._gemini_live_client.start_session` ist der Reconnection-Loop.
            # Er wird seine Events (inkl. Session Resumption Updates) hierher liefern.
            async for response_event_from_gemini_live in self._gemini_live_client.start_session(
                audio_input_queue=self.audio_input_queue,
                video_input_queue=self.video_input_queue,
                text_input_queue=self.text_input_queue,
                audio_output_callback=audio_output_cb,
                audio_interrupt_callback=audio_interrupt_cb,
            ):
                # Jedes Event von Gemini Live bedeutet Aktivität
                self._last_activity_time = time.time() # <-- WICHTIG: Reset Inaktivitäts-Zeit
                
                if not response_event_from_gemini_live:
                    continue

                # logger.info(f"RESPONSE TYPE from gemini_live.py: {type(response_event_from_gemini_live)}")
                # logger.debug(f"FULL RESPONSE from gemini_live.py: {response_event_from_gemini_live}")

                response_type = response_event_from_gemini_live.get("type")

                if response_type == "gemini":
                    # Text-Transkription aus Gemini's output
                    text = response_event_from_gemini_live.get("text")
                    if text:
                        self._current_ai_response_buffer += text
                        ai_response_event = AIResponseEvent(
                            text=text,
                            timestamp=datetime.utcnow()
                        )
                        await self.ws_manager.broadcast(ai_response_event)
                        # logger.info(f"AI Response (Text): {text}")
                
                elif response_type == "user":
                    # Text-Transkription aus Gemini's input (des Nutzers)
                    text = response_event_from_gemini_live.get("text")
                    if text:
                        participant_id, username = self._get_active_identity()
                        source_client_type = "unknown"
                        identity_client = self.ws_manager.get_identity_client()
                        if identity_client and identity_client.state:
                            source_client_type = getattr(
                                identity_client.state.client_type,
                                "value",
                                str(identity_client.state.client_type),
                            )
                        await self.log_interaction(
                            participant_id=participant_id,
                            username=username,
                            source_client_type=source_client_type,
                            interaction_type="user_transcript",
                            content=text,
                        )
                        transcript_event = TranscriptEvent(
                            text=text,
                            is_final=True,
                            timestamp=datetime.utcnow()
                        )
                        await self.ws_manager.broadcast(transcript_event)
                        logger.info(f"User Transcript: {text}")

                elif response_type == "tool_call":
                    logger.debug(f"Received tool_call notification from gemini_live.py event_queue: {response_event_from_gemini_live}")
                
                elif response_type == "turn_complete":
                    if self._current_ai_response_buffer.strip():
                        self._last_ai_response_text = self._current_ai_response_buffer.strip()
                        participant_id, username = self._get_active_identity()
                        await self.log_interaction(
                            participant_id=participant_id,
                            username=username,
                            source_client_type="gemini",
                            interaction_type="ai_response",
                            content=self._last_ai_response_text,
                        )
                    self._current_ai_response_buffer = ""
                    await self.ws_manager.broadcast(TurnCompleteEvent(timestamp=datetime.utcnow()))
                    logger.debug("Gemini turn complete.")
                
                elif response_type == "interrupted":
                    if self._current_ai_response_buffer.strip():
                        self._last_ai_response_text = self._current_ai_response_buffer.strip()
                    self._current_ai_response_buffer = ""
                    logger.debug("Gemini interrupted.")
                
                elif response_type == "error":
                    error_msg = response_event_from_gemini_live.get("error", "Unknown error from Gemini Live.")
                    logger.error(f"Error from Gemini Live event_queue: {error_msg}")
                    await self.ws_manager.broadcast(ErrorEvent(message=f"Gemini Live Error: {error_msg}", timestamp=datetime.utcnow()))
                
                # elif response_type == "session_resumption_update": # <-- NEU: Behandle dieses Event
                #     # GeminiLive Client managed _current_session_handle selbst, hier nur Log
                #     logger.info(f"Session resumption update received in GeminiSessionManager: {response_event_from_gemini_live}")

                elif response_type == "go_away": # <-- NEU: Behandle dieses Event
                    # GeminiLive Client managed reconnect, hier nur Log und Systemnachricht
                    logger.warning(f"Gemini Live signaled GoAway. Reconnection handled by GeminiLive client. Time left: {response_event_from_gemini_live.get('time_left')}")
                    await self.ws_manager.broadcast(SystemMessageEvent(message="Gemini Live signaling connection close. Attempting to reconnect."))
                
                elif response_type == "aborted":
                    logger.info("Gemini Live reported transient abort (1008). Reconnection handled by GeminiLive client.")

                else:
                    logger.warning(f"Unhandled event type from gemini_live.py event_queue: {response_type}")
                    logger.debug(f"Full unhandled event: {response_event_from_gemini_live}")

        except asyncio.CancelledError:
            logger.info(RED + "Gemini session runner task cancelled." + RESET)
        except Exception as e:
            logger.error(RED + f"Critical error in Gemini session runner: {e}" + RESET, exc_info=True)
        finally:
            logger.info("Gemini session runner exiting.")
            # Important: The _run_gemini_session task has completed.
            # This doesn't mean the session is fully stopped, _gemini_live_client.start_session()
            # manages its own reconnection loop. We only stop our tasks if explicitly called.


    async def stop_session(self, announce: bool = True, reset_gemini_client: bool = False):
        """Stops the Gemini Live session and associated tasks."""
        if not (self._gemini_session_task and not self._gemini_session_task.done()): # <-- Prüfe, ob Task läuft
            logger.info(ORANGE + "Gemini session is not running." + RESET)
            if reset_gemini_client:
                self._gemini_live_client = None
            self._response_mode = "text"
            return

        logger.info(GREEN + "Stopping Gemini session tasks gracefully." + RESET)
        # self._is_running = False # <-- Nicht mehr benötigt

        if self._inactivity_monitor_task: # <-- NEU: Inaktivitäts-Monitor stoppen
            self._inactivity_monitor_task.cancel()
            try:
                await self._inactivity_monitor_task
            except asyncio.CancelledError:
                pass
            self._inactivity_monitor_task = None

        if self._gemini_session_task:
            self._gemini_session_task.cancel()
            try:
                await self._gemini_session_task
            except asyncio.CancelledError:
                pass
            self._gemini_session_task = None # Setze den Task auf None

        if self._tool_response_task:
            self._tool_response_task.cancel()
            try:
                await self._tool_response_task
            except asyncio.CancelledError:
                pass
            self._tool_response_task = None # Setze den Task auf None

        # Clear queues
        # Wichtig: Queues leeren, wenn die Session wirklich beendet wird, um keine alten Daten zu behalten
        # wenn der Benutzer später eine neue Session startet.
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

        if reset_gemini_client:
            self._gemini_live_client = None

        logger.info(GREEN + "GeminiSessionManager stopped." + RESET)
        if announce:
            await self.ws_manager.broadcast(SystemMessageEvent(message="Gemini session has been stopped."))

    async def interrupt_session(self):
        """Stops the current Gemini stream but keeps the resumable context."""
        await self.stop_session(announce=False, reset_gemini_client=False)

    async def reset_session(self):
        """Drops the current Gemini context and starts a clean replacement session."""
        await self.stop_session(announce=False, reset_gemini_client=True)
        await self.start_session(announce=False)
        await self.ws_manager.broadcast(SessionResetEvent(message="Started a new Gemini session with fresh context."))