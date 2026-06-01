# squishy_pi_client/client/websocket_client.py

import asyncio
import websockets
from typing import TypedDict
from typing_extensions import Literal
import json
import logging
from datetime import datetime
from typing import Callable, Any, Dict, Optional, List, Union

from config import CLIENT_CAPABILITIES

logger = logging.getLogger(__name__)

# --- Typen für Backend-Nachrichten ---
# Basis-Event, alle anderen JSON-Events erben davon
class IncomingBackendJsonEvent(TypedDict):
    type: str

class RegistrationAckEvent(IncomingBackendJsonEvent):
    type: Literal["registration_ack"]
    client_id: str
    message: str
    active_controller_id: Optional[str]
    current_active_controller_type: Optional[str]

class ActiveControllerChangeEvent(IncomingBackendJsonEvent):
    type: Literal["active_controller_change"]
    new_active_controller_id: str
    new_active_controller_type: str

class AIResponseEvent(IncomingBackendJsonEvent):
    type: Literal["ai_response"]
    text: str

class TranscriptEvent(IncomingBackendJsonEvent):
    type: Literal["transcript"]
    text: str
    is_final: bool

class ToolCallEvent(IncomingBackendJsonEvent):
    type: Literal["tool_call"]
    tool_name: str
    args: Dict[str, Any]
    suggested_action: str # Hinzugefügt, da es im main.py verwendet wird

class SystemMessageEvent(IncomingBackendJsonEvent): # Annahme, dass es diese geben könnte
    type: Literal["system_message"]
    message: str

class ErrorEvent(IncomingBackendJsonEvent): # Annahme, dass es diese geben könnte
    type: Literal["error"]
    message: str

# Union-Typ für alle möglichen JSON-Events
AllIncomingJsonEvents = Union[
    RegistrationAckEvent,
    ActiveControllerChangeEvent,
    AIResponseEvent,
    TranscriptEvent,
    ToolCallEvent,
    SystemMessageEvent,
    ErrorEvent,
]

# Wir geben entweder geparste JSON-Objekte oder rohe Audio-Bytes weiter
# Die Callbacks sollten asyncio.Coroutinen sein, da sie awaitable sein müssen
MessageCallback = Callable[[Union[AllIncomingJsonEvents, bytes]], Any] # Any, da es ein Coroutine sein kann
OnConnectCallback = Callable[[], Any]
OnErrorCallback = Callable[[Exception], Any]


class WebSocketClient:
    def __init__(self,
                 ws_url: str,
                 client_type: str,
                 capabilities: List[str],
                 on_message_callback: MessageCallback,
                 on_connect_callback: Optional[OnConnectCallback] = None, # Optional gemacht
                 on_error_callback: Optional[OnErrorCallback] = None): # Optional gemacht
        
        self.ws_url = ws_url
        self.client_type = client_type
        self.capabilities = capabilities
        self._on_message_callback = on_message_callback
        self._on_connect_callback = on_connect_callback
        self._on_error_callback = on_error_callback

        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._client_id: Optional[str] = None
        self._active_controller_id: Optional[str] = None
        self._active_controller_type: Optional[str] = None
        self._is_connected = False
        self._listener_task: Optional[asyncio.Task] = None # Task für _listen_for_messages

        # Callbacks für Audio- und Sensor-Daten (Platzhalter für später)
        # self._audio_sender_callback: Optional[Callable[[bytes], None]] = None # Nicht mehr benötigt, da send_audio_chunk direkt genutzt wird
        self._sensor_event_sender_callback: Optional[Callable[[str, str, Any, Optional[str]], Any]] = None # Any, da async
        self._tool_call_handler: Optional[Callable[[str, Dict[str, Any], str], Any]] = None # Hinzugefügt suggested_action

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def client_id(self) -> Optional[str]:
        return self._client_id

    @property
    def active_controller_id(self) -> Optional[str]:
        return self._active_controller_id

    @property
    def active_controller_type(self) -> Optional[str]:
        return self._active_controller_type

    # Entferne set_audio_sender, da send_audio_chunk direkt eine Methode des Clients ist

    def set_sensor_event_sender(self, callback: Callable[[str, str, Any, Optional[str]], Any]):
        """Setzt den Callback zum Senden von Sensor-Events an das Backend. Erwartet einen awaitable."""
        self._sensor_event_sender_callback = callback

    def set_tool_call_handler(self, callback: Callable[[str, Dict[str, Any], str], Any]):
        """Setzt den Handler für eingehende Tool-Calls vom Backend. Erwartet einen awaitable."""
        self._tool_call_handler = callback

    async def connect(self):
        logger.info(f"Attempting to connect to WebSocket at {self.ws_url}")
        try:
            self._websocket = await asyncio.wait_for(websockets.connect(self.ws_url), timeout=10) # Timeout erhöht
            self._is_connected = True
            logger.info("WebSocket connected. Sending registration...")
            await self._register_client()
            if self._on_connect_callback:
                # Da _on_connect_callback ein Coroutine sein könnte, awaiten wir es
                if asyncio.iscoroutinefunction(self._on_connect_callback):
                    await self._on_connect_callback()
                else:
                    self._on_connect_callback()
            
            self._listener_task = asyncio.create_task(self._listen_for_messages())

        except asyncio.TimeoutError:
            logger.error(f"WebSocket connection timed out after 10 seconds: No response from {self.ws_url}")
            self._is_connected = False
            if self._on_error_callback:
                if asyncio.iscoroutinefunction(self._on_error_callback):
                    await self._on_error_callback(asyncio.TimeoutError("timed out during opening handshake"))
                else:
                    self._on_error_callback(asyncio.TimeoutError("timed out during opening handshake"))
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket specific connection failed: {e}")
            self._is_connected = False
            if self._on_error_callback:
                if asyncio.iscoroutinefunction(self._on_error_callback):
                    await self._on_error_callback(e)
                else:
                    self._on_error_callback(e)
        except Exception as e:
            logger.error(f"General connection error: {e}")
            self._is_connected = False
            if self._on_error_callback:
                if asyncio.iscoroutinefunction(self._on_error_callback):
                    await self._on_error_callback(e)
                else:
                    self._on_error_callback(e)

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._websocket:
            logger.info("Disconnecting WebSocket.")
            await self._websocket.close()
            self._is_connected = False
            self._client_id = None
            self._active_controller_id = None
            self._active_controller_type = None
            logger.info("WebSocket disconnected.")

    async def _register_client(self):
        register_message = {
            "type": "register",
            "timestamp": datetime.now().isoformat(),
            "client_type": self.client_type,
            "capabilities": self.capabilities,
        }
        await self._send_json(register_message)

    async def _listen_for_messages(self):
        while self._is_connected and self._websocket:
            try:
                message = await self._websocket.recv()
                
                if isinstance(message, bytes):
                    # _on_message_callback kann eine Coroutine sein
                    if asyncio.iscoroutinefunction(self._on_message_callback):
                        asyncio.create_task(self._on_message_callback(message))
                    else:
                        self._on_message_callback(message)
                elif isinstance(message, str):
                    try:
                        parsed_data: AllIncomingJsonEvents = json.loads(message)
                        logger.debug(f"Received JSON: {parsed_data.get('type')}")

                        # Handle registration_ack internally
                        if parsed_data.get("type") == "registration_ack":
                            ack: RegistrationAckEvent = parsed_data
                            self._client_id = ack.get("client_id")
                            self._active_controller_id = ack.get("active_controller_id")
                            self._active_controller_type = ack.get("current_active_controller_type")
                            logger.info(f"Registered as {self.client_type} with ID {self._client_id}. "
                                        f"Active Controller: {self._active_controller_type} ({self._active_controller_id})")
                        # Handle active_controller_change internally
                        elif parsed_data.get("type") == "active_controller_change":
                            change: ActiveControllerChangeEvent = parsed_data
                            self._active_controller_id = change.get("new_active_controller_id")
                            self._active_controller_type = change.get("new_active_controller_type")
                            logger.info(f"Active controller changed to: {self._active_controller_type} ({self._active_controller_id})")
                        # Handle tool_call (for later)
                        elif parsed_data.get("type") == "tool_call":
                            tool_call: ToolCallEvent = parsed_data
                            if self._tool_call_handler:
                                # Tool handler kann await sein, daher asyncio.create_task
                                asyncio.create_task(
                                    self._tool_call_handler(
                                        tool_call.get("tool_name", ""),
                                        tool_call.get("args", {}),
                                        tool_call.get("suggested_action", "")
                                    )
                                )
                            
                        # Für alle JSON-Nachrichten, auch die intern gehandhabten, den externen Callback aufrufen
                        if asyncio.iscoroutinefunction(self._on_message_callback):
                            asyncio.create_task(self._on_message_callback(parsed_data))
                        else:
                            self._on_message_callback(parsed_data)

                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON string message: {message}")
                    except Exception as e:
                        logger.error(f"Error processing JSON message: {e}", exc_info=True)
                else:
                    logger.warning(f"Received unexpected message type: {type(message)} - {message}")

            except websockets.exceptions.ConnectionClosedOK:
                logger.info("WebSocket connection closed gracefully (OK).")
                break
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"WebSocket connection closed with error: {e}", exc_info=True)
                if self._on_error_callback:
                    if asyncio.iscoroutinefunction(self._on_error_callback):
                        await self._on_error_callback(e)
                    else:
                        self._on_error_callback(e)
                break
            except asyncio.CancelledError:
                logger.info("WebSocket listener task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}", exc_info=True)
                if self._on_error_callback:
                    if asyncio.iscoroutinefunction(self._on_error_callback):
                        await self._on_error_callback(e)
                    else:
                        self._on_error_callback(e)
                break
        self._is_connected = False
        self._websocket = None # Setze WebSocket auf None nach dem Beenden
        logger.info("Stopped listening for WebSocket messages.")


    async def _send_json(self, data: Dict[str, Any]):
        if self._websocket and self._is_connected:
            try:
                await self._websocket.send(json.dumps(data))
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Tried to send JSON on a closed WebSocket.")
                self._is_connected = False
            except Exception as e:
                logger.error(f"Failed to send JSON message: {e}", exc_info=True)
                if self._on_error_callback:
                    if asyncio.iscoroutinefunction(self._on_error_callback):
                        await self._on_error_callback(e)
                    else:
                        self._on_error_callback(e)
        else:
            logger.warning("WebSocket not connected, cannot send JSON data.")

    async def send_text_message(self, text: str):
        """Sends a text message to the backend."""
        message = {
            "type": "text_message",
            "timestamp": datetime.now().isoformat(),
            "text": text
        }
        await self._send_json(message)

    async def send_audio_chunk(self, audio_bytes: bytes):
        """Sends raw audio bytes to the backend."""
        if self._websocket and self._is_connected:
            try:
                await self._websocket.send(audio_bytes)
                # logger.debug(f"Sending audio chunk of size {len(audio_bytes)} bytes.")
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Tried to send audio on a closed WebSocket.")
                self._is_connected = False
            except Exception as e:
                logger.error(f"Failed to send audio chunk: {e}", exc_info=True)
                if self._on_error_callback:
                    if asyncio.iscoroutinefunction(self._on_error_callback):
                        await self._on_error_callback(e)
                    else:
                        self._on_error_callback(e)
        else:
            logger.debug("WebSocket not connected, cannot send audio chunk.") # Debug statt Warning, da oft normal wenn nicht aktiv

    async def send_sensor_event(self, sensor_id: str, event_type: str, value: Any, intensity: Optional[str] = None):
        """Sends a simulated sensor event to the backend."""
        message = {
            "type": "sensor_event",
            "timestamp": datetime.now().isoformat(),
            "sensor_id": sensor_id,
            "event": event_type,
            "value": value,
            "intensity": intensity
        }
        await self._send_json(message)
    
    async def request_set_active_controller(self):
        """Requests to become the active controller."""
        if self._client_id:
            message = {
                "type": "set_active_controller",
                "timestamp": datetime.now().isoformat(),
                "client_id": self._client_id
            }
            await self._send_json(message)
        else:
            logger.warning("Client ID not set, cannot request active controller.")