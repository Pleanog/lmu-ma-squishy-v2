# FILE: app/websocket/router.py

import logging
from typing import Callable, Coroutine, Any, Dict

from models.events import ErrorEvent, IncomingEventType, IncomingEvent
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

    async def route_message(self, event: IncomingEventType, client_id: str):
        """
        Main routing logic for incoming events from WebSocket clients.
        """
        client = self.ws_manager.get_client(client_id)
        if not client or not client.state:
            logger.warning(f"Event from unknown or unregistered client {client_id}. Dropping.")
            return

        is_active_controller = (client_id == self.ws_manager.active_controller_id)

        should_start_session = False

        # --- Handle Active Controller Input ---
        if is_active_controller:
            if isinstance(event, IncomingEvent.AUDIO_CHUNK.model):
                if ClientCapability.AUDIO_INPUT in client.state.capabilities:
                    should_start_session = True
                    await self.gemini_session.audio_input_queue.put(event.data)
                    logger.debug(f"Client {client_id} (active controller) sent audio chunk.")
                else:
                    logger.warning(f"Active controller {client_id} lacks AUDIO_INPUT capability.")
            elif isinstance(event, IncomingEvent.TEXT_MESSAGE.model):
                if ClientCapability.TEXT_INPUT in client.state.capabilities:
                    should_start_session = True
                    await self.gemini_session.text_input_queue.put(event.text)
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
                    sensor_text = f"System: Sensor '{event.sensor_id}' detected event '{event.event}' with value '{event.value}'."
                    if event.intensity:
                        sensor_text += f" Intensity: {event.intensity}."
                    await self.gemini_session.text_input_queue.put(sensor_text)
                    logger.info(f"Hardware client {client_id} (active controller) sent sensor event: {event.sensor_id}")
                elif client.state.client_type == ClientType.FRONTEND and ClientCapability.SENSOR_SIMULATION in client.state.capabilities:
                    # Frontend simulates sensor event
                    should_start_session = True
                    simulated_sensor_text = f"System (simulated): Sensor '{event.sensor_id}' detected event '{event.event}' with value '{event.value}'."
                    if event.intensity:
                        simulated_sensor_text += f" Intensity: {event.intensity}."
                    await self.gemini_session.text_input_queue.put(simulated_sensor_text)
                    logger.info(f"Frontend client {client_id} (active controller, simulating) sent sensor event: {event.sensor_id}")
                else:
                    logger.warning(f"Client {client_id} sent sensor event but lacks capability or is not active controller for this input.")
            elif isinstance(event, IncomingEvent.TOOL_RESPONSE.model):
                # Tool responses are always handled by GeminiSessionManager
                await self.gemini_session.tool_response_queue.put((event.tool_call_id, event.tool_name, event.result))
                logger.debug(f"Client {client_id} sent tool response for {event.tool_name}/{event.tool_call_id}.")
            else:
                logger.warning(f"Client {client_id} (active controller) sent unhandled event type: {event.type}")
        else:
            # --- Handle Observer/Debugger Input (Non-Active Controller) ---
            # These clients can send some events, but not primary conversation inputs
            if isinstance(event, IncomingEvent.SENSOR_EVENT.model):
                # Observers can send sensor events, but it's treated as a simulation/debug input
                if client.state.client_type == ClientType.FRONTEND and ClientCapability.SENSOR_SIMULATION in client.state.capabilities:
                    simulated_sensor_text = f"System (simulated by observer {client.client_id}): Sensor '{event.sensor_id}' detected event '{event.event}' with value '{event.value}'."
                    if event.intensity:
                        simulated_sensor_text += f" Intensity: {event.intensity}."
                    await self.gemini_session.text_input_queue.put(simulated_sensor_text)
                    logger.info(f"Frontend client {client_id} (observer, simulating) sent sensor event: {event.sensor_id}")
                else:
                    logger.warning(f"Client {client_id} (observer) sent sensor event but lacks simulation capability.")
            elif isinstance(event, IncomingEvent.TEXT_MESSAGE.model):
                 # Non-active clients can send text messages, but they are treated as system/debug inputs for Gemini
                 # This prevents observers from directly conversing with Gemini
                 system_text = f"System (from {client.state.client_type} observer {client.client_id}): {event.text}"
                 await self.gemini_session.text_input_queue.put(system_text)
                 logger.info(f"Observer client {client_id} sent text message as system input.")
            elif isinstance(event, IncomingEvent.IMAGE_CHUNK.model):
                # Always allow image input, active controller or not, if Gemini supports it
                await self.gemini_session.video_input_queue.put(event.data)
                logger.debug(f"Client {client_id} sent image chunk.")
            elif isinstance(event, IncomingEvent.TOOL_RESPONSE.model):
                # Tool responses are always handled by GeminiSessionManager, regardless of active controller
                await self.gemini_session.tool_response_queue.put((event.tool_call_id, event.tool_name, event.result))
                logger.debug(f"Client {client_id} sent tool response for {event.tool_name}/{event.tool_call_id}.")
            else:
                logger.warning(f"Client {client_id} (observer) sent unhandled event type: {event.type}. Ignoring.")
                await client.send_event(ErrorEvent(message="You are not the active controller. Input ignored or treated as system message."))

        if should_start_session and not self.gemini_session.is_session_active:
            await self.gemini_session.start_session()