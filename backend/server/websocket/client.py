import asyncio
import logging
import json
from typing import AsyncGenerator, Dict, Any, Union, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from models.client_state import WebSocketClientState, ClientType, ClientCapability
# Importiere AudioOutputEvent explizit, damit isinstance() funktioniert
from models.events import IncomingEventType, IncomingEvent, OutgoingEventType, BaseEvent, ErrorEvent, AudioOutputEvent 

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

class WebSocketClient:
    """
    Manages a single WebSocket connection and its associated client state.
    """
    def __init__(self, websocket: WebSocket):
        self.websocket: WebSocket = websocket
        self.client_id: str = str(uuid4())
        self.state: Optional[WebSocketClientState] = None
        self._send_queue: asyncio.Queue[Union[OutgoingEventType, bytes]] = asyncio.Queue()
        self._send_task: Optional[asyncio.Task] = None
        self._disconnect_event: asyncio.Event = asyncio.Event()
        logger.info(f"{GREEN}Client {self.client_id}: Initialized.{RESET}")

    async def accept(self):
        await self.websocket.accept()
        logger.info(f"{GREEN}Client {self.client_id}: WebSocket accepted.{RESET}")
        self._send_task = asyncio.create_task(self._send_loop())

    def set_state(
        self,
        client_type: ClientType,
        capabilities: Set[ClientCapability],
        username: Optional[str] = None,
        participant_id: Optional[str] = None,
    ):
        self.state = WebSocketClientState(
            client_id=self.client_id,
            client_type=client_type,
            capabilities=capabilities,
            username=username.strip() if isinstance(username, str) and username.strip() else None,
            participant_id=participant_id.strip() if isinstance(participant_id, str) and participant_id.strip() else None,
        )
        logger.info(
            f"{GREY}Client {self.client_id}: State set to "
            f"{self.state.client_type} with capabilities: {self.state.capabilities}"
            f" and username: {self.state.username}"
            f" and participant_id: {self.state.participant_id}{RESET}"
        )

    async def send_event(self, event: OutgoingEventType):
        if self._disconnect_event.is_set():
            logger.warning(f"Client {self.client_id}: Attempted to send event after disconnect signal.")
            return
        await self._send_queue.put(event)

    async def _send_loop(self):
        """Continuously sends messages from the queue to the WebSocket."""
        try:
            while not self._disconnect_event.is_set():
                event = await self._send_queue.get()
                
                # HIER IST DIE WICHTIGE ANPASSUNG
                if isinstance(event, AudioOutputEvent):
                    # AudioOutputEvent enthält rohe Bytes im 'data'-Feld.
                    # Diese müssen direkt mit websocket.send_bytes gesendet werden.
                    await self.websocket.send_bytes(event.data)
                    logger.debug(f"Client {self.client_id}: Sent AudioOutputEvent (bytes).")
                    
                    # Optional: Wenn du Metadaten (type, timestamp) separat als JSON senden möchtest,
                    # könntest du hier ein weiteres JSON-Event senden. Aber für reines Audio-Streaming
                    # ist das Senden der rohen Bytes oft ausreichend.
                    # await self.websocket.send_text(json.dumps({
                    #     "type": event.type,
                    #     "timestamp": event.timestamp.isoformat()
                    # }))
                    
                elif isinstance(event, BaseEvent):
                    # Alle anderen Pydantic-Events (die von BaseEvent erben) werden als JSON gesendet.
                    # Pydantic's model_dump_json() serialisiert datetime-Objekte standardmäßig korrekt.
                    await self.websocket.send_text(event.model_dump_json())
                    logger.debug(f"Client {self.client_id}: Sent {event.type} event (JSON).")
                    
                elif isinstance(event, bytes):
                    # Dies ist der Fall, falls du jemals direkt rohe Bytes (nicht verpackt in einem Event-Objekt)
                    # an die _send_queue sendest.
                    await self.websocket.send_bytes(event)
                    logger.debug(f"Client {self.client_id}: Sent raw bytes directly.")
                else:
                    logger.warning(f"Client {self.client_id}: Attempted to send unsupported type: {type(event)}")
                
                self._send_queue.task_done()
        except WebSocketDisconnect:
            logger.info(ORANGE + f"Client {self.client_id}: WebSocket disconnected during send loop." + RESET)
            self._disconnect_event.set()
        except asyncio.CancelledError:
            logger.info(ORANGE + f"Client {self.client_id}: Send loop cancelled." + RESET)
            self._disconnect_event.set()
        except Exception as e:
            logger.error(f"Client {self.client_id}: Error in send loop: {e}", exc_info=True)
            self._disconnect_event.set()
        finally:
            asyncio.create_task(self.disconnect())


    async def receive_events(self) -> AsyncGenerator[IncomingEventType, None]:
        """Asynchronously yields incoming events from the WebSocket."""
        try:
            while not self._disconnect_event.is_set():
                message = await self.websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    raise WebSocketDisconnect

                if message.get("text"):
                    text_data = message["text"]
                    try:
                        data = json.loads(text_data)
                        event_type_str = data.get("type")

                        if not event_type_str:
                            logger.warning(f"Client {self.client_id}: Received text message without 'type': {data}")
                            # Send an error back to the client
                            await self.send_event(ErrorEvent(message="Received text message without 'type' field."))
                            continue

                        try:
                            event_type = IncomingEvent(event_type_str)
                            event_model = event_type.model
                            event = event_model(**data)
                            yield event
                        except ValueError:
                            logger.warning(f"Client {self.client_id}: Unknown incoming event type: {event_type_str}")
                            await self.send_event(ErrorEvent(message=f"Unknown event type: {event_type_str}"))
                        except ValidationError as ve:
                            logger.error(f"Client {self.client_id}: Validation error for {event_type_str}: {ve.errors()} Data: {data}")
                            await self.send_event(ErrorEvent(message=f"Invalid event data for {event_type_str}: {ve.errors()}"))
                        except Exception as e:
                            logger.error(f"Client {self.client_id}: Error processing incoming text event: {e}", exc_info=True)
                            await self.send_event(ErrorEvent(message=f"Server error processing text event: {e.__class__.__name__}"))

                    except json.JSONDecodeError:
                        logger.warning(f"Client {self.client_id}: Received non-JSON text: {text_data}")
                        # Treat as a generic text message if not JSON for now, or just drop/error
                        # For now, we will drop it as it's not a structured event
                        await self.send_event(ErrorEvent(message="Received non-JSON text. Expected structured event."))


                elif message.get("bytes"):
                    # Assuming raw bytes are always audio chunks for the backend
                    yield IncomingEvent.AUDIO_CHUNK.model(data=message["bytes"])

        except WebSocketDisconnect:
            logger.info(ORANGE + f"Client {self.client_id}: WebSocket disconnected." + RESET)
            self._disconnect_event.set()
        except asyncio.CancelledError:
            logger.info(ORANGE + f"Client {self.client_id}: Receive loop cancelled." + RESET)
            self._disconnect_event.set()
        except Exception as e:
            logger.error(f"Client {self.client_id}: Error in receive loop: {e}", exc_info=True)
            self._disconnect_event.set()
        finally:
            # Ensure disconnect is called only once
            asyncio.create_task(self.disconnect())

    async def disconnect(self):
        """Cleans up resources when the client disconnects."""
        if self._disconnect_event.is_set(): # Already in the process of disconnecting
            return

        self._disconnect_event.set() # Signal all loops to stop

        logger.info(f"Client {self.client_id}: Initiating disconnect.")

        if self._send_task:
            self._send_task.cancel()
            try:
                # Give it a small timeout to finish, or just let it be cancelled
                await asyncio.wait_for(self._send_task, timeout=1.0)
            except asyncio.CancelledError:
                logger.debug(f"Client {self.client_id}: Send task cancelled.")
            except asyncio.TimeoutError:
                logger.warning(f"Client {self.client_id}: Send task did not terminate gracefully.")
            except Exception as e:
                logger.error(f"Client {self.client_id}: Error awaiting send task: {e}")

        # The receive loop usually terminates first due to WebSocketDisconnect
        # No explicit cancellation needed if it's already finished.

        try:
            if self.websocket.client_state != 3: # WebSocketState.DISCONNECTED (enum value 3)
                await self.websocket.close()
            logger.info(f"Client {self.client_id}: WebSocket closed.")
        except Exception as e:
            logger.debug(f"Client {self.client_id}: Error during final websocket close (may already be closed or connection lost): {e}")

        logger.info(f"Client {self.client_id}: Disconnected and cleaned up.")