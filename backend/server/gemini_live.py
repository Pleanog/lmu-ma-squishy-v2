import asyncio
import inspect
import logging
import traceback

logger = logging.getLogger(__name__)
from google import genai
from google.genai import types
from system_promt import system_promt;

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


def _is_benign_live_abort(error: Exception) -> bool:
    """Returns True for expected transient Live disconnects (policy 1008 aborted)."""
    status_code = getattr(error, "status_code", None)
    message = str(error).lower()
    if status_code == 1008:
        return True
    return "1008" in message and "operation was aborted" in message

class GeminiLive:
    """
    Handles the interaction with the Gemini Live API.
    """
    def __init__(self, api_key, model, input_sample_rate, tools=None, tool_mapping=None, system_prompt=None):
        """
        Initializes the GeminiLive client.

        Args:
            api_key (str): The Gemini API Key.
            model (str): The model name to use.
            input_sample_rate (int): The sample rate for audio input.
            tools (list, optional): List of tools to enable. Defaults to None.
            tool_mapping (dict, optional): Mapping of tool names to functions. Defaults to None.
            system_prompt (str, optional): The system instruction to send to Gemini.
        """
        self.api_key = api_key
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.client = genai.Client(api_key=api_key)
        self.tools = tools or []
        self.tool_mapping = tool_mapping or {}
        self.system_prompt = system_prompt or system_promt
        self._current_session_handle = None # Speichert den Handle für die Wiederaufnahme der Session
        self._client_message_index = 0 # Um den letzten gesendeten Nachrichtenindex zu verfolgen
        self._last_sent_client_message_index = 0 # Trackt den Index der zuletzt gesendeten Nachricht für die Wiederaufnahme
        self._resumption_config_cls = getattr(types, "LiveSessionResumptionConfig", None)
        self._supports_session_resumption = self._resumption_config_cls is not None
        self._resumption_support_warning_logged = False

    def set_system_prompt(self, system_prompt: str):
        self.system_prompt = system_prompt

    def clear_session_resumption_state(self):
        self._current_session_handle = None
        self._client_message_index = 0
        self._last_sent_client_message_index = 0

    async def _connect_and_receive(self, audio_input_queue, video_input_queue, text_input_queue, audio_output_callback, audio_interrupt_callback):
        """Internal method to handle a single connection attempt and receive loop."""
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
            system_instruction=types.Content(parts=[types.Part(text=self.system_prompt)]),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY",
            ),
            tools=self.tools,
        )
                
        if self._current_session_handle and self._supports_session_resumption:
            config.session_resumption_config = self._resumption_config_cls(
                session_handle=self._current_session_handle,
                last_consumed_client_message_index=self._client_message_index
            )
            logger.info(f"Attempting to resume Gemini Live session with handle: {self._current_session_handle}, starting client_message_index from {self._client_message_index}")
        elif self._current_session_handle and not self._supports_session_resumption:
            if not self._resumption_support_warning_logged:
                logger.warning(
                    "Session resumption handle exists, but this google.genai.types version "
                    "does not provide LiveSessionResumptionConfig. Falling back to fresh sessions."
                )
                self._resumption_support_warning_logged = True
            self.clear_session_resumption_state()
            logger.info(f"Connecting to Gemini Live with model={self.model} (resumption disabled by SDK capabilities)")
        else:
            logger.info(f"Connecting to Gemini Live with model={self.model}")
            self._last_sent_client_message_index = 0 # Reset for new session

        async with self.client.aio.live.connect(model=self.model, config=config) as session:
            logger.info(GREEN + "Gemini Live session opened successfully" + RESET + (f" (resumed with handle: {self._current_session_handle})" if self._current_session_handle else ""))
            
            async def send_audio():
                try:
                    while True:
                        chunk = await audio_input_queue.get()
                        self._last_sent_client_message_index += 1
                        await session.send_realtime_input(
                            audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={self.input_sample_rate}")
                        )
                except asyncio.CancelledError:
                    logger.debug("send_audio task cancelled")
                except Exception as e:
                    logger.error(f"send_audio error: {e}\n{traceback.format_exc()}")

            async def send_video():
                try:
                    while True:
                        chunk = await video_input_queue.get()
                        self._last_sent_client_message_index += 1
                        logger.info(f"Sending video frame to Gemini: {len(chunk)} bytes")
                        await session.send_realtime_input(
                            video=types.Blob(data=chunk, mime_type="image/jpeg")
                        )
                except asyncio.CancelledError:
                    logger.debug("send_video task cancelled")
                except Exception as e:
                    logger.error(f"send_video error: {e}\n{traceback.format_exc()}")

            async def send_text():
                try:
                    while True:
                        text = await text_input_queue.get()
                        self._last_sent_client_message_index += 1
                        logger.info(f"Sending text to Gemini: {text}")
                        await session.send_realtime_input(text=text)
                except asyncio.CancelledError:
                    logger.debug("send_text task cancelled")
                except Exception as e:
                    logger.error(f"send_text error: {e}\n{traceback.format_exc()}")

            event_queue = asyncio.Queue()


            async def receive_loop_inner():
                try:
                    while True:
                        async for response in session.receive():

                            if response.go_away:
                                logger.warning(ORANGE + f"Received GoAway from Gemini: {response.go_away.time_left}. Initiating graceful shutdown." + RESET)
                                await event_queue.put({"type": "go_away", "time_left": response.go_away.time_left})
                                return # Exit receive loop
                            
                            session_resumption_update = getattr(response, "session_resumption_update", None)
                            if session_resumption_update:
                                self._current_session_handle = session_resumption_update.new_handle
                                if session_resumption_update.last_consumed_client_message_index is not None:
                                    self._client_message_index = session_resumption_update.last_consumed_client_message_index
                                    self._last_sent_client_message_index = max(self._last_sent_client_message_index, self._client_message_index)

                                # logger.info(f"Session resumption update: new_handle='{self._current_session_handle}' resumable={session_resumption_update.resumable} last_consumed_client_message_index={self._client_message_index}")
                                await event_queue.put({"type": "session_resumption_update", "handle": self._current_session_handle, "resumable": session_resumption_update.resumable, "last_consumed_client_message_index": self._client_message_index})

                            server_content = response.server_content
                            tool_call = response.tool_call
                            
                            if server_content:
                                if server_content.model_turn:
                                    for part in server_content.model_turn.parts:
                                        if part.inline_data:
                                            # logger.info(GREY + f"Gemini audio chunk: {len(part.inline_data.data)} bytes" + RESET)
                                            if inspect.iscoroutinefunction(audio_output_callback):
                                                await audio_output_callback(part.inline_data.data)
                                            else:
                                                audio_output_callback(part.inline_data.data)
                                
                                if server_content.input_transcription and server_content.input_transcription.text:
                                    await event_queue.put({"type": "user", "text": server_content.input_transcription.text})

                                if server_content.output_transcription and server_content.output_transcription.text:
                                    await event_queue.put({"type": "gemini", "text": server_content.output_transcription.text})
                                    logger.debug( CYAN + f"{server_content.output_transcription.text}" + RESET  )
        
                                if server_content.turn_complete:
                                    last_consumed_index = session_resumption_update.last_consumed_client_message_index if session_resumption_update else None
                                    logger.info(f"Turn complete. last_consumed_client_message_index={last_consumed_index}")
                                    await event_queue.put({"type": "turn_complete"})

                                
                                if server_content.interrupted:
                                    if audio_interrupt_callback:
                                        if inspect.iscoroutinefunction(audio_interrupt_callback):
                                            await audio_interrupt_callback()
                                        else:
                                            audio_interrupt_callback()
                                    await event_queue.put({"type": "interrupted"}) 
                                    logger.info("Received interruption signal from Gemini.")

                            if tool_call:
                                function_responses = []
                                for fc in tool_call.function_calls:
                                    func_name = fc.name
                                    args = fc.args or {}
                                    
                                    if func_name in self.tool_mapping:
                                        try:
                                            tool_func = self.tool_mapping[func_name]
                                            if inspect.iscoroutinefunction(tool_func):
                                                result = await tool_func(**args)
                                            else:
                                                loop = asyncio.get_running_loop()
                                                result = await loop.run_in_executor(None, lambda: tool_func(**args))
                                        except Exception as e:
                                            result = f"Error: {e}"
                                        
                                        function_responses.append(types.FunctionResponse(
                                            name=func_name,
                                            id=fc.id,
                                            response={"result": result}
                                        ))
                                        await event_queue.put({"type": "tool_call", "name": func_name, "args": args, "result": result})
                                        logger.info(f"Handled tool call for '{func_name}' with args {args} and result {result}")
                                await session.send_tool_response(function_responses=function_responses)
                        
                        # session.receive() iterator ended (e.g. after turn_complete) — re-enter to keep listening
                        logger.debug("Gemini receive iterator completed, re-entering receive loop")

                except asyncio.CancelledError:
                    logger.debug("receive_loop task cancelled")
                except Exception as e:
                    if _is_benign_live_abort(e):
                        logger.warning(
                            "Gemini Live receive loop ended with policy 1008 'operation was aborted'. "
                            "Treating as transient and reconnecting."
                        )
                        await event_queue.put({"type": "aborted", "reason": f"{type(e).__name__}: {e}"})
                    else:
                        logger.error(f"receive_loop error: {type(e).__name__}: {e}\n{traceback.format_exc()}")
                        await event_queue.put({"type": "error", "error": f"{type(e).__name__}: {e}"})
                finally:
                    logger.info("receive_loop exiting")
                    await event_queue.put(None)

            send_audio_task = asyncio.create_task(send_audio())
            send_video_task = asyncio.create_task(send_video())
            send_text_task = asyncio.create_task(send_text())
            receive_task = asyncio.create_task(receive_loop_inner())

            try:
                while True:
                    event = await event_queue.get()
                    if event is None: # Loop finished or error
                        break
                    yield event
            finally:
                logger.info("Cleaning up Gemini Live session tasks for current connection")
                send_audio_task.cancel()
                send_video_task.cancel()
                send_text_task.cancel()
                receive_task.cancel()
                await asyncio.gather(send_audio_task, send_video_task, send_text_task, receive_task, return_exceptions=True) # Ensure tasks are cleaned up

    async def start_session(self, audio_input_queue, video_input_queue, text_input_queue, audio_output_callback, audio_interrupt_callback=None):
        """
        Manages the lifecycle of the Gemini Live session, including reconnections.
        """
        reconnection_delay = 1  # seconds
        max_reconnection_delay = 60 # seconds
        
        while True:
            try:
                # Iterate over the internal connection and its events
                async for event in self._connect_and_receive(audio_input_queue, video_input_queue, text_input_queue, audio_output_callback, audio_interrupt_callback):
                    if event.get("type") == "go_away":
                        logger.info(f"Gemini Live session explicitly asked to close. Attempting to reconnect in {reconnection_delay}s.")
                        break # Exit inner async for loop to trigger outer while loop for reconnect
                    elif event.get("type") == "aborted":
                        logger.info(
                            "Gemini Live session aborted by remote side (1008). "
                            f"Attempting to reconnect in {reconnection_delay}s."
                        )
                        break
                    elif event.get("type") == "error":
                        logger.error(f"Error within Gemini Live session: {event.get('error')}. Attempting to reconnect in {reconnection_delay}s.")
                        yield event # Propagate the error
                        break # Exit inner async for loop for reconnect
                    yield event # Propagate all other events

                # If we broke out of the inner loop (due to GoAway or error), attempt reconnect
                await asyncio.sleep(reconnection_delay)
                reconnection_delay = min(reconnection_delay * 2, max_reconnection_delay) # Exponential backoff

            except Exception as e:
                logger.error(f"Critical error in Gemini Live session management: {type(e).__name__}: {e}\n{traceback.format_exc()}")
                # Yield error to the main app if it's a critical, non-recoverable error at this level
                yield {"type": "error", "error": f"Critical Gemini Live error: {type(e).__name__}: {e}"}
                await asyncio.sleep(reconnection_delay) # Wait before trying again
                reconnection_delay = min(reconnection_delay * 2, max_reconnection_delay)

            finally:
                logger.info("Gemini Live outer session loop preparing for next connection attempt.")