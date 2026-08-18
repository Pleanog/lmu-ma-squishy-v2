# FILE: app/websocket/router.py

import logging
from typing import Any, Dict, Optional

from gemini.session import GeminiSessionManager
from models.client_state import ClientCapability, ClientType
from models.events import (
    AudioInterruptEvent,
    ErrorEvent,
    IncomingEvent,
    IncomingEventType,
    SensorObservedEvent,
    SystemCommandEvent,
    SystemMessageEvent,
)
from tools.dispatcher import ToolDispatcher
from websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes incoming WebSocket events to Gemini and tools.
    Frontend handles text/audio conversation; hardware/frontend can both send sensor input.
    """

    def __init__(self, ws_manager: WebSocketManager, gemini_session: GeminiSessionManager, tool_dispatcher: ToolDispatcher):
        self.ws_manager = ws_manager
        self.gemini_session = gemini_session
        self.tool_dispatcher = tool_dispatcher
        self.ws_manager.message_router = self.route_message
        logger.info("MessageRouter initialized.")

        self._gesture_system_injections: Dict[str, str] = {
            "drop_on_table": "[System Sensors] Gesture 'drop_on_table' detected. Please repeat what you just said more briefly.",
            "tap_head": "[System Sensors] Gesture 'tap_head' detected. Please, explain the last important piece of information in more detail and more comprehensively.",
            "target_focus": "[System Sensors] Gesture 'target_focus' detected. Summarize the last important piece of information very briefly in a few words and confirm that it has been saved in the browser's local storage.",
            "shake": "[System Sensors] Gesture 'shake' detected. The user wants to hear other options or alternative suggestions to the last answer. Provide them now.",
            "squeeze": "[System Sensors] Gesture 'squeeze' detected. Help the user optimize their last question or prompt; take the asked question and rephrase it in a more precise, clear, and effective way, give it back to the user, and state that you will now answer this new prompt."
        }
        self._gesture_aliases: Dict[str, str] = {
            "activate": "press_head",
            "hush_geste": "hush",
            "hush_geste": "hush",
            "place_on_table": "drop_on_table",
        }
        self._known_gestures = set(self._gesture_system_injections.keys()) | {
            "press_head",
            "hush",
            "horizontal_turn",
        }

    def _can_send_sensor_events(self, client) -> bool:
        capabilities = client.state.capabilities
        return (
            ClientCapability.SENSOR_INPUT in capabilities
            or ClientCapability.SENSOR_SIMULATION in capabilities
        )

    def _is_system_sensorik_text(self, text: str) -> bool:
        return text.strip().startswith("[System Sensors]")

    def _is_save_trigger_text(self, text: str) -> bool:
        lowered = text.lower()
        return self._is_system_sensorik_text(text) and (
            "target_focus" in lowered or "r5_save" in lowered or "save_memory" in lowered
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

    def _normalize_gesture_name(self, raw_event_name: Optional[str]) -> Optional[str]:
        gesture_name = (raw_event_name or "").strip()
        if not gesture_name:
            return None
        if gesture_name in self._known_gestures:
            return gesture_name
        return self._gesture_aliases.get(gesture_name)

    async def _broadcast_sensor_observed(self, event, client, mapped_gesture: Optional[str] = None) -> None:
        await self.ws_manager.broadcast(
            SensorObservedEvent(
                sensor_id=event.sensor_id,
                event=event.event,
                value=event.value,
                intensity=event.intensity,
                source_client_type=client.state.client_type if client.state else None,
                mapped_gesture=mapped_gesture,
            )
        )

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

    async def _handle_gesture_event(self, event, client) -> bool:
        if not self._can_send_sensor_events(client):
            await client.send_event(ErrorEvent(message="Client lacks capability to send gesture events."))
            return False

        raw_gesture_name = (event.event or "").strip()

        print(f"\033[94mReceived gesture: '{raw_gesture_name}' from client {client.client_id if client else 'unknown'}\033[0m")

        gesture_name = self._normalize_gesture_name(raw_gesture_name)
        if not gesture_name:
            if not raw_gesture_name:
                await client.send_event(ErrorEvent(message="Gesture sensor events require an 'event' name."))
            else:
                await client.send_event(ErrorEvent(message=f"Unknown gesture event: {raw_gesture_name}"))
            return False

        await self._log_client_interaction(
            client,
            interaction_type="gesture_event",
            content=gesture_name,
            metadata={"sensor_id": event.sensor_id},
        )

        if gesture_name == "hush":
            await self.ws_manager.broadcast(AudioInterruptEvent(message="AI audio interrupted by gesture."))
            await self.ws_manager.broadcast(
                SystemCommandEvent(command="set_microphone_state", target="frontend", payload={"enabled": False})
            )
            await self.gemini_session.interrupt_session()
            return False

        if gesture_name == "press_head":
            # await self.gemini_session.reset_session()
            await self.ws_manager.broadcast(
                SystemCommandEvent(command="set_microphone_state", target="frontend", payload={"enabled": True})
            )
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
        client = self.ws_manager.get_client(client_id)
        if not client or not client.state:
            logger.warning("Event from unknown or unregistered client %s. Dropping.", client_id)
            return

        should_start_session = False

        if isinstance(event, IncomingEvent.SENSOR_EVENT.model):
            mapped_gesture = self._normalize_gesture_name(event.event)
            await self._broadcast_sensor_observed(event, client, mapped_gesture=mapped_gesture)

            if mapped_gesture:
                event.event = mapped_gesture
                should_start_session = await self._handle_gesture_event(event, client)
                if should_start_session and not self.gemini_session.is_session_active:
                    await self.gemini_session.start_session()
                return

        if isinstance(event, IncomingEvent.AUDIO_CHUNK.model):
            if client.state.client_type != ClientType.FRONTEND or ClientCapability.AUDIO_INPUT not in client.state.capabilities:
                await client.send_event(ErrorEvent(message="Only frontend clients may send audio input."))
                return
            should_start_session = True
            self.gemini_session.set_response_mode_for_audio_input()
            await self.gemini_session.audio_input_queue.put(event.data)
            return await self._start_session_if_needed(should_start_session)

        if isinstance(event, IncomingEvent.TEXT_MESSAGE.model):
            if client.state.client_type != ClientType.FRONTEND or ClientCapability.TEXT_INPUT not in client.state.capabilities:
                await client.send_event(ErrorEvent(message="Only frontend clients may send text input."))
                return

            if self._is_save_trigger_text(event.text):
                await self._log_client_interaction(
                    client,
                    interaction_type="save_trigger_text",
                    content=event.text,
                )
                save_result = await self.gemini_session.save_latest_response_as_memory(
                    source="frontend_system_sensorik",
                    trigger_event="target_focus_text",
                )
                status_message = (
                    f"Memory saved ({save_result.get('memory_id')})"
                    if save_result.get("status") == "saved"
                    else f"Memory save failed: {save_result.get('message')}"
                )
                await client.send_event(SystemMessageEvent(message=status_message))
                return

            should_start_session = True
            self.gemini_session.set_response_mode_for_text_input()
            await self.gemini_session.text_input_queue.put(event.text)
            await self._log_client_interaction(
                client,
                interaction_type="text_input",
                content=event.text,
            )
            return await self._start_session_if_needed(should_start_session)

        if isinstance(event, IncomingEvent.IMAGE_CHUNK.model):
            if client.state.client_type != ClientType.FRONTEND:
                await client.send_event(ErrorEvent(message="Only frontend clients may send image input."))
                return
            should_start_session = True
            await self.gemini_session.video_input_queue.put(event.data)
            return await self._start_session_if_needed(should_start_session)

        if isinstance(event, IncomingEvent.SENSOR_EVENT.model):
            if not self._can_send_sensor_events(client):
                await client.send_event(ErrorEvent(message="Client lacks capability to send sensor events."))
                return

            should_start_session = True
            source_prefix = (
                "System (simulated)"
                if ClientCapability.SENSOR_SIMULATION in client.state.capabilities
                else "System"
            )
            sensor_text = self._build_sensor_message(event, source_prefix)
            await self.gemini_session.text_input_queue.put(sensor_text)
            await self._log_client_interaction(
                client,
                interaction_type=(
                    "sensor_simulation"
                    if ClientCapability.SENSOR_SIMULATION in client.state.capabilities
                    else "sensor_input"
                ),
                content=sensor_text,
                metadata={"sensor_id": event.sensor_id, "event": event.event, "intensity": event.intensity},
            )
            return await self._start_session_if_needed(should_start_session)

        if isinstance(event, IncomingEvent.TOOL_RESPONSE.model):
            await self.gemini_session.tool_response_queue.put((event.tool_call_id, event.tool_name, event.result))
            await self._log_client_interaction(
                client,
                interaction_type="tool_response",
                content=event.tool_name,
                metadata={"tool_call_id": event.tool_call_id, "result": event.result},
            )
            return

        if isinstance(event, IncomingEvent.KEEPALIVE.model):
            logger.debug("Keepalive received from client %s.", client_id)
            return

        await client.send_event(ErrorEvent(message=f"Unhandled event type: {event.type}"))

    async def _start_session_if_needed(self, should_start_session: bool):
        if should_start_session and not self.gemini_session.is_session_active:
            await self.gemini_session.start_session()
