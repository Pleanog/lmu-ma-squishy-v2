# squishy_pi_client/client/websocket_client.py

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Callable, Any, Dict, Optional, List, Union

from config import CLIENT_CAPABILITIES

logger = logging.getLogger(__name__)

# --- Typen für Backend-Nachrichten (vereinfacht für Text-Chat) ---
class IncomingBackendJsonEvent:
    type: str

class RegistrationAckEvent(IncomingBackendJsonEvent):
    client_id: str
    message: str
    active_controller_id: Optional[str]
    current_active_controller_type: Optional[str]

class AIResponseEvent(IncomingBackendJsonEvent):
    text: str

# Wir geben entweder geparste JSON-Objekte oder rohe Audio-Bytes weiter
MessageCallback = Callable[[Union[IncomingBackendJsonEvent, bytes]], Any]
OnConnectCallback = Callable[[], Any]
OnErrorCallback = Callable[[Exception], Any]


class WebSocketClient:
    def __init__(self,
                 ws_url: str,
                 client_type: str,
                 capabilities: List[str],
                 on_message_callback: MessageCallback,
                 on_connect_callback: OnConnectCallback = None,
                 on_error_callback: OnErrorCallback = None):
        
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

        # Callbacks für Audio- und Sensor-Daten (Platzhalter für später)
        self._audio_sender_callback: Optional[Callable[[bytes], None]] = None
        self._sensor_event_sender_callback: Optional[Callable[[str, str, Any, Optional[str]], None]] = None
        self._tool_call_handler: Optional[Callable[[str, Dict[str, Any]], None]] = None

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

    def set_audio_sender(self, callback: Callable[[bytes], None]):
        """Setzt den Callback zum Senden von Audio-Chunks an das Backend."""
        self._audio_sender_callback = callback

    def set_sensor_event_sender(self, callback: Callable[[str, str, Any, Optional[str]], None]):
        """Setzt den Callback zum Senden von Sensor-Events an das Backend."""
        self._sensor_event_sender_callback = callback

    def set_tool_call_handler(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Setzt den Handler für eingehende Tool-Calls vom Backend."""
        self._tool_call_handler = callback

    async def connect(self):
        logger.info(f"Attempting to connect to WebSocket at {self.ws_url}")
        try:
            self._websocket = await asyncio.wait_for(websockets.connect(self.ws_url), timeout=5)
            self._is_connected = True
            logger.info("WebSocket connected. Sending registration...")
            await self._register_client()
            if self._on_connect_callback:
                self._on_connect_callback()
            
            asyncio.create_task(self._listen_for_messages())

        except asyncio.TimeoutError:
            logger.error(f"WebSocket connection timed out after 5 seconds: No response from {self.ws_url}")
            self._is_connected = False
            if self._on_error_callback:
                self._on_error_callback(asyncio.TimeoutError("timed out during opening handshake"))
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket specific connection failed: {e}")
            self._is_connected = False
            if self._on_error_callback:
                self._on_error_callback(e)
        except Exception as e:
            logger.error(f"General connection error: {e}")
            self._is_connected = False
            if self._on_error_callback:
                self._on_error_callback(e)

    async def disconnect(self):
        if self._websocket:
            logger.info("Disconnecting WebSocket.")
            await self._websocket.close()
            self._is_connected = False
            self._client_id = None
            self._active_controller_id = None
            self._active_controller_type = None

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
                
                # Check for binary data (audio)
                if isinstance(message, bytes):
                    self._on_message_callback(message)
                elif isinstance(message, str):
                    try:
                        parsed_data = json.loads(message)
                        logger.debug(f"Received JSON: {parsed_data}")

                        # Handle registration_ack internally
                        if parsed_data.get("type") == "registration_ack":
                            ack = parsed_data # as RegistrationAckEvent
                            self._client_id = ack.get("client_id")
                            self._active_controller_id = ack.get("active_controller_id")
                            self._active_controller_type = ack.get("current_active_controller_type")
                            logger.info(f"Registered as {self.client_type} with ID {self.client_id}. "
                                        f"Active Controller: {self._active_controller_type} ({self._active_controller_id})")
                            self._on_message_callback(parsed_data) # Also pass ack to main app
                        # Handle active_controller_change internally
                        elif parsed_data.get("type") == "active_controller_change":
                            change = parsed_data
                            self._active_controller_id = change.get("new_active_controller_id")
                            self._active_controller_type = change.get("new_active_controller_type")
                            logger.info(f"Active controller changed to: {self._active_controller_type} ({self._active_controller_id})")
                            self._on_message_callback(parsed_data) # Also pass to main app
                        # Handle tool_call (for later)
                        elif parsed_data.get("type") == "tool_call":
                            if self._tool_call_handler:
                                tool_name = parsed_data.get("tool_name")
                                args = parsed_data.get("args", {})
                                await self._tool_call_handler(tool_name, args)
                            self._on_message_callback(parsed_data) # Also pass to main app
                        else:
                            # For all other JSON messages (e.g., ai_response, transcript, system_message)
                            self._on_message_callback(parsed_data)

                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON string message: {message}")
                        # You could pass this raw string to the callback if needed
                        # self._on_message_callback(message)
                else:
                    logger.warning(f"Received unexpected message type: {type(message)} - {message}")
                    # Hier könnte auch ein Blob ankommen, wenn die WebSocket-Library es so sendet.
                    # websockets sendet normalerweise str für Text und bytes für Binär.
                    # Wenn es ein Blob ist, müsste es hier ähnlich wie im TS-Frontend behandelt werden:
                    # if isinstance(message, Blob):
                    #    array_buffer = await message.arrayBuffer()
                    #    self._on_message_callback(array_buffer)
                    # For Python, websockets typically gives bytes for binary data.

            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket connection closed gracefully.")
                break
            except Exception as e:
                logger.error(f"Error while listening for messages: {e}")
                break
        self._is_connected = False
        logger.info("Stopped listening for WebSocket messages.")


    async def _send_json(self, data: Dict[str, Any]):
        if self._websocket and self._is_connected:
            await self._websocket.send(json.dumps(data))
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

    # Platzhalter für die zukünftige Implementierung von Audio- und Sensor-Senden
    async def send_audio_chunk(self, audio_bytes: bytes):
        """Sends raw audio bytes to the backend."""
        if self._websocket and self._is_connected:
            # logger.debug(f"Sending audio chunk of size {len(audio_bytes)} bytes.")
            await self._websocket.send(audio_bytes)
        else:
            logger.warning("WebSocket not connected, cannot send audio chunk.")

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

    async def send_initiate_persona_greeting(self):
        """Sends a request to the backend to initiate the AI's persona greeting."""
        if self._client_id:
            message = {
                "type": "initiate_persona_greeting",
                "timestamp": datetime.now().isoformat(),
                "client_id": self._client_id
            }
            await self._send_json(message)
        else:
            logger.warning("Client ID not set, cannot send persona greeting initiation.")