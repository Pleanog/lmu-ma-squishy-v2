# FILE: app/websocket/router.py

import logging
from typing import Callable, Coroutine, Any, Dict, Optional

from models.events import AudioInterruptEvent, ErrorEvent, IncomingEventType, IncomingEvent, SystemMessageEvent
from websocket.manager import WebSocketManager
from gemini.session import GeminiSessionManager
from tools.dispatcher import ToolDispatcher
from models.client_state import ClientCapability, ClientType

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

class MessageRouter:
    """
    Routes incoming WebSocket events to the appropriate handlers.
    This class orchestrates communication between WebSocket clients,
    the Gemini session, and tool dispatchers.
    """
    def __init__(self, ws_manager: WebSocketManager, gemini_session: GeminiSessionManager, tool_dispatcher: ToolDispatcher):
        self.ws_manager = ws_manager
        self.gemini_session = gemini_session
        self.tool_dispatcher = tool_dispatcher
        self.ws_manager.message_router = self.route_message # Inject this router into the manager
        logger.info("MessageRouter initialized.")

        self._gesture_system_injections: Dict[str, str] = {
            "place_on_table": "[System-Sensorik] Geste 'place_on_table' erkannt. Fasse deine Antworten ab sofort deutlich kürzer und prägnanter zusammen.",
            "multi_tap_head_open_hand": "[System-Sensorik] Geste 'multi_tap_head_open_hand' erkannt. Erkläre das aktuelle Thema ab sofort detaillierter und ausführlicher.",
            "target_focus": "[System-Sensorik] Geste 'target_focus' erkannt. Fasse die letzte wichtige Information sehr knapp zusammen in wenigen Worten und bestätige, dass sie im lokalen Speicher des Browsers gespeichert wurde.",
            "vertical_shake": "[System-Sensorik] Geste 'vertical_shake' erkannt. Der Nutzer möchte andere Optionen oder alternative Vorschläge zur letzten Antwort hören. Gib ihm diese jetzt.",
            "squeeze_sides": "[System-Sensorik] Geste 'squeeze_sides' erkannt. Hilf dem Nutzer, seine letzte Frage oder seinen letzten Prompt zu optimieren, nimm die gestellte Frage und formuliere sie in einer präziseren, klareren und effektiveren Weise um gib sie dem Nutzer zurück, sage, dass du jetzt diesen neuen Promt beantworten wirst",
        }

    def _can_send_sensor_events(self, client) -> bool:
        if client.state.client_type == ClientType.HARDWARE:
            return ClientCapability.SENSOR_INPUT in client.state.capabilities
        if client.state.client_type == ClientType.FRONTEND:
            return ClientCapability.SENSOR_SIMULATION in client.state.capabilities
        return False

    def _is_system_sensorik_text(self, text: str) -> bool:
        return text.strip().startswith("[System-Sensorik]")

    def _is_save_trigger_text(self, text: str) -> bool:
        lowered = text.lower()
        return self._is_system_sensorik_text(text) and (
            "target_focus" in lowered or
            "r5_save" in lowered or
            "save_memory" in lowered
        )

    def _build_sensor_message(self, event, source_prefix: str) -> str:
        parts = [f"{source_prefix}: Sensor '{event.sensor_id}'"]
        if event.event:
            parts.append(f"detected event '{event.event}'")
        if event.value is not None:
            parts.append(f"with value '{event.value}'")
        sensor_text = " ".join(parts) + "."
        if event.intensity:
            sensor_text += f" Intensity: {event.intensity}."
        return sensor_text

    async def _log_client_interaction(
        self,
        client,
        interaction_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not client or not client.state:
            return
        participant_id = client.state.participant_id or f"anonymous-{client.client_id[:8]}"
        username = client.state.username or "Gast"
        source_client_type = getattr(client.state.client_type, "value", str(client.state.client_type))
        await self.gemini_session.log_interaction(
            participant_id=participant_id,
            username=username,
            source_client_type=source_client_type,
            interaction_type=interaction_type,
            content=content,
            metadata=metadata,
        )

    def _get_preferred_audio_controller_id(self, fallback_client_id: str) -> Optional[str]:
        for candidate_id, candidate in self.ws_manager.active_clients.items():
            if candidate.state and candidate.state.client_type == ClientType.HARDWARE and candidate.state.capabilities.intersection(
                {ClientCapability.AUDIO_INPUT, ClientCapability.TEXT_INPUT}
            ):
                return candidate_id

        fallback_client = self.ws_manager.get_client(fallback_client_id)
        if fallback_client and fallback_client.state and fallback_client.state.capabilities.intersection(
            {ClientCapability.AUDIO_INPUT, ClientCapability.TEXT_INPUT}
        ):
            return fallback_client_id

        return self.ws_manager.active_controller_id

    async def _handle_gesture_event(self, event, client) -> bool:
        if event.sensor_id != "gesture":
            return False

        if not self._can_send_sensor_events(client):
            logger.warning(f"Client {client.client_id} attempted gesture routing without sensor capability.")
            await client.send_event(ErrorEvent(message="Client lacks capability to send gesture events."))
            return False

        gesture_name = (event.event or "").strip()
        if not gesture_name:
            await client.send_event(ErrorEvent(message="Gesture sensor events require an 'event' name."))
            return False

        logger.info(f"Routing gesture '{gesture_name}' from {client.state.client_type} client {client.client_id}.")
        await self._log_client_interaction(
            client,
            interaction_type="gesture_event",
            content=gesture_name,
            metadata={"sensor_id": event.sensor_id},
        )

        if gesture_name == "firm_press_head":
            preferred_controller_id = self._get_preferred_audio_controller_id(client.client_id)
            if preferred_controller_id:
                await self.ws_manager.set_active_controller(preferred_controller_id)
            return True

        if gesture_name == "hush_gesture":
            await self.ws_manager.broadcast(
                AudioInterruptEvent(message="AI audio interrupted by gesture.")
            )
            await self.gemini_session.interrupt_session()
            return False

        if gesture_name == "horizontal_turn":
            await self.gemini_session.reset_session()
            return False

        if gesture_name == "target_focus":
            save_result = await self.gemini_session.save_latest_response_as_memory(
                source="gesture_target_focus",
                trigger_event="target_focus",
            )
            status_message = (
                f"Memory saved ({save_result.get('memory_id')})"
                if save_result.get("status") == "saved"
                else f"Memory save failed: {save_result.get('message')}"
            )
            await client.send_event(SystemMessageEvent(message=status_message))
            return False

        system_injection = self._gesture_system_injections.get(gesture_name)
        if system_injection:
            await self.gemini_session.text_input_queue.put(system_injection)
            return True

        await client.send_event(ErrorEvent(message=f"Unknown gesture event: {gesture_name}"))
        return False

    async def route_message(self, event: IncomingEventType, client_id: str):
        """
        Main routing logic for incoming events from WebSocket clients.
        """
        client = self.ws_manager.get_client(client_id)
        if not client or not client.state:
            logger.warning(f"Event from unknown or unregistered client {client_id}. Dropping.")
            return

        is_active_controller = (client_id == self.ws_manager.active_controller_id)
        routing = self.ws_manager.get_routing_config()

        should_start_session = False

        if isinstance(event, IncomingEvent.SENSOR_EVENT.model) and event.sensor_id == "gesture":
            should_start_session = await self._handle_gesture_event(event, client)
            if should_start_session and not self.gemini_session.is_session_active:
                await self.gemini_session.start_session()
            return

        # --- Handle Active Controller Input ---
        if is_active_controller:
            if isinstance(event, IncomingEvent.AUDIO_CHUNK.model):
                if ClientCapability.AUDIO_INPUT in client.state.capabilities:
                    if client.state.client_type == ClientType.HARDWARE and not routing.get("hardware_mic_enabled", True):
                        await client.send_event(SystemMessageEvent(message="Hardware mic routing is disabled. Audio input ignored."))
                        return
                    should_start_session = True
                    self.ws_manager.note_input_route(client_id, "audio")
                    await self.gemini_session.audio_input_queue.put(event.data)
                    logger.debug(f"Client {client_id} (active controller) sent audio chunk.")
                else:
                    logger.warning(f"Active controller {client_id} lacks AUDIO_INPUT capability.")
            elif isinstance(event, IncomingEvent.TEXT_MESSAGE.model):
                if self._is_save_trigger_text(event.text):
                    await self._log_client_interaction(
                        client,
                        interaction_type="save_trigger_text",
                        content=event.text,
                    )
                    save_result = await self.gemini_session.save_latest_response_as_memory(
                        source="hardware_system_sensorik",
                        trigger_event="target_focus_text",
                    )
                    status_message = (
                        f"Memory saved ({save_result.get('memory_id')})"
                        if save_result.get("status") == "saved"
                        else f"Memory save failed: {save_result.get('message')}"
                    )
                    await client.send_event(SystemMessageEvent(message=status_message))
                    return
                if ClientCapability.TEXT_INPUT in client.state.capabilities:
                    if (
                        client.state.client_type == ClientType.FRONTEND
                        and not self._is_system_sensorik_text(event.text)
                        and not routing.get("ui_text_mode_enabled", True)
                    ):
                        await client.send_event(SystemMessageEvent(message="UI text mode is disabled. Text input ignored."))
                        return
                    should_start_session = True
                    self.ws_manager.note_input_route(client_id, "text")
                    await self.gemini_session.text_input_queue.put(event.text)
                    await self._log_client_interaction(
                        client,
                        interaction_type="text_input",
                        content=event.text,
                    )
                    logger.debug(f"Client {client_id} (active controller) sent text message.")
                else:
                    logger.warning(f"Active controller {client_id} lacks TEXT_INPUT capability.")
            elif isinstance(event, IncomingEvent.IMAGE_CHUNK.model):
                # Always allow image input, active controller or not, if Gemini supports it
                should_start_session = True
                await self.gemini_session.video_input_queue.put(event.data)
                logger.debug(f"Client {client_id} sent image chunk.")
            elif isinstance(event, IncomingEvent.SENSOR_EVENT.model):
                if client.state.client_type == ClientType.HARDWARE and ClientCapability.SENSOR_INPUT in client.state.capabilities:
                    # Translate sensor event to natural language for Gemini
                    should_start_session = True
                    self.ws_manager.note_input_route(client_id, "sensor")
                    sensor_text = self._build_sensor_message(event, "System")
                    await self.gemini_session.text_input_queue.put(sensor_text)
                    await self._log_client_interaction(
                        client,
                        interaction_type="sensor_input",
                        content=sensor_text,
                        metadata={"sensor_id": event.sensor_id, "event": event.event, "intensity": event.intensity},
                    )
                    logger.info(f"Hardware client {client_id} (active controller) sent sensor event: {event.sensor_id}")
                elif client.state.client_type == ClientType.FRONTEND and ClientCapability.SENSOR_SIMULATION in client.state.capabilities:
                    # Frontend simulates sensor event
                    should_start_session = True
                    self.ws_manager.note_input_route(client_id, "sensor")
                    simulated_sensor_text = self._build_sensor_message(event, "System (simulated)")
                    await self.gemini_session.text_input_queue.put(simulated_sensor_text)
                    await self._log_client_interaction(
                        client,
                        interaction_type="sensor_simulation",
                        content=simulated_sensor_text,
                        metadata={"sensor_id": event.sensor_id, "event": event.event, "intensity": event.intensity},
                    )
                    logger.info(f"Frontend client {client_id} (active controller, simulating) sent sensor event: {event.sensor_id}")
                else:
                    logger.warning(f"Client {client_id} sent sensor event but lacks capability or is not active controller for this input.")
            elif isinstance(event, IncomingEvent.TOOL_RESPONSE.model):
                # Tool responses are always handled by GeminiSessionManager
                await self.gemini_session.tool_response_queue.put((event.tool_call_id, event.tool_name, event.result))
                await self._log_client_interaction(
                    client,
                    interaction_type="tool_response",
                    content=event.tool_name,
                    metadata={"tool_call_id": event.tool_call_id, "result": event.result},
                )
                logger.debug(f"Client {client_id} sent tool response for {event.tool_name}/{event.tool_call_id}.")
            else:
                logger.warning(f"Client {client_id} (active controller) sent unhandled event type: {event.type}")
        else:
            # --- Handle Observer/Debugger Input (Non-Active Controller) ---
            # These clients can send some events, but not primary conversation inputs
            if isinstance(event, IncomingEvent.SENSOR_EVENT.model):
                # Observers can send sensor events, but it's treated as a simulation/debug input
                if client.state.client_type == ClientType.FRONTEND and ClientCapability.SENSOR_SIMULATION in client.state.capabilities:
                   should_start_session = True
                   self.ws_manager.note_input_route(client_id, "sensor")
                   simulated_sensor_text = self._build_sensor_message(event, f"System (simulated by observer {client.client_id})")
                   await self.gemini_session.text_input_queue.put(simulated_sensor_text)
                   await self._log_client_interaction(
                       client,
                       interaction_type="sensor_simulation_observer",
                       content=simulated_sensor_text,
                       metadata={"sensor_id": event.sensor_id, "event": event.event, "intensity": event.intensity},
                   )
                   logger.info(f"Frontend client {client_id} (observer, simulating) sent sensor event: {event.sensor_id}")
                elif client.state.client_type == ClientType.HARDWARE and ClientCapability.SENSOR_INPUT in client.state.capabilities:
                   should_start_session = True
                   self.ws_manager.note_input_route(client_id, "sensor")
                   sensor_text = self._build_sensor_message(event, f"System (hardware observer {client.client_id})")
                   await self.gemini_session.text_input_queue.put(sensor_text)
                   await self._log_client_interaction(
                       client,
                       interaction_type="sensor_input_observer",
                       content=sensor_text,
                       metadata={"sensor_id": event.sensor_id, "event": event.event, "intensity": event.intensity},
                   )
                   logger.info(f"Hardware client {client_id} (observer) sent sensor event: {event.sensor_id}")
                else:
                   logger.warning(f"Client {client_id} (observer) sent sensor event but lacks simulation capability.")
            elif isinstance(event, IncomingEvent.TEXT_MESSAGE.model):
                if self._is_save_trigger_text(event.text):
                   await self._log_client_interaction(
                       client,
                       interaction_type="save_trigger_text_observer",
                       content=event.text,
                   )
                   save_result = await self.gemini_session.save_latest_response_as_memory(
                       source=f"{client.state.client_type}_observer_system_sensorik",
                       trigger_event="target_focus_text",
                   )
                   status_message = (
                       f"Memory saved ({save_result.get('memory_id')})"
                       if save_result.get("status") == "saved"
                       else f"Memory save failed: {save_result.get('message')}"
                   )
                   await client.send_event(SystemMessageEvent(message=status_message))
                   return
                if self._is_system_sensorik_text(event.text):
                   should_start_session = True
                   self.ws_manager.note_input_route(client_id, "text")
                   await self.gemini_session.text_input_queue.put(event.text)
                   await self._log_client_interaction(
                       client,
                       interaction_type="system_sensorik_text",
                       content=event.text,
                   )
                   logger.info(f"Forwarded out-of-band sensor text from {client.state.client_type} client {client_id}.")
                else:
                   if client.state.client_type == ClientType.FRONTEND and not routing.get("ui_text_mode_enabled", True):
                       await client.send_event(SystemMessageEvent(message="UI text mode is disabled. Text input ignored."))
                       return
                   # Non-active clients can send text messages, but they are treated as system/debug inputs for Gemini
                   # This prevents observers from directly conversing with Gemini
                   should_start_session = True
                   self.ws_manager.note_input_route(client_id, "text")
                   system_text = f"System (from {client.state.client_type} observer {client.client_id}): {event.text}"
                   await self.gemini_session.text_input_queue.put(system_text)
                   await self._log_client_interaction(
                       client,
                       interaction_type="observer_text_input",
                       content=event.text,
                   )
                   logger.info(f"Observer client {client_id} sent text message as system input.")
            elif isinstance(event, IncomingEvent.IMAGE_CHUNK.model):
                # Always allow image input, active controller or not, if Gemini supports it
                should_start_session = True
                await self.gemini_session.video_input_queue.put(event.data)
                logger.debug(f"Client {client_id} sent image chunk.")
            elif isinstance(event, IncomingEvent.TOOL_RESPONSE.model):
                # Tool responses are always handled by GeminiSessionManager, regardless of active controller
                await self.gemini_session.tool_response_queue.put((event.tool_call_id, event.tool_name, event.result))
                await self._log_client_interaction(
                   client,
                   interaction_type="tool_response_observer",
                   content=event.tool_name,
                   metadata={"tool_call_id": event.tool_call_id, "result": event.result},
                )
                logger.debug(f"Client {client_id} sent tool response for {event.tool_name}/{event.tool_call_id}.")
            else:
                logger.warning(f"Client {client_id} (observer) sent unhandled event type: {event.type}. Ignoring.")
                await client.send_event(ErrorEvent(message="You are not the active controller. Input ignored or treated as system message."))

        if should_start_session and not self.gemini_session.is_session_active:
            await self.gemini_session.start_session()