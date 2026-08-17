# FILE: app/websocket/manager.py

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, Optional

from fastapi import WebSocket

from models.client_state import ClientCapability, ClientType
from models.events import (
    ErrorEvent,
    IncomingEventType,
    RegisterEvent,
    RegistrationAckEvent,
    RoutingConfigUpdateEvent,
    SensorEvent,
    KeepAliveEvent,
    SetActiveControllerEvent,
    SystemMessageEvent,
)
from websocket.client import WebSocketClient

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages all active WebSocket connections and client registration.
    Active-controller/routing-control logic is intentionally disabled.
    """

    def __init__(self):
        self.active_clients: Dict[str, WebSocketClient] = {}
        self.gemini_session_manager: Optional[Any] = None
        self.event_queue: asyncio.Queue[tuple[str, IncomingEventType]] = asyncio.Queue()
        self.message_router: Optional[Callable[[IncomingEventType, str], Coroutine[Any, Any, None]]] = None
        self._hardware_last_keepalive_ts: Optional[float] = None
        self._hardware_last_activity_ts: Optional[float] = None
        logger.info("WebSocketManager initialized.")

    async def connect(self, websocket: WebSocket) -> WebSocketClient:
        client = WebSocketClient(websocket)
        await client.accept()
        self.active_clients[client.client_id] = client
        logger.info(
            "\033[32mClient %s connected. Total active clients: %s\033[0m",
            client.client_id,
            len(self.active_clients),
        )
        await asyncio.sleep(0)
        return client

    async def disconnect(self, client_id: str):
        client = self.active_clients.pop(client_id, None)
        if not client:
            logger.warning("Attempted to disconnect non-existent client: %s", client_id)
            return

        logger.info(
            "\033[33mClient %s disconnected. Total active clients: %s\033[0m",
            client_id,
            len(self.active_clients),
        )
        await self.broadcast(
            SystemMessageEvent(
                message=f"{client.state.client_type if client.state else 'Unknown'} client ({client.client_id[:8]}) disconnected."
            )
        )

    async def register_client(self, client: WebSocketClient, event: RegisterEvent):
        if client.state:
            logger.warning("Client %s already registered. Ignoring re-registration.", client.client_id)
            await client.send_event(ErrorEvent(message="Client already registered."))
            return

        client.set_state(
            event.client_type,
            set(event.capabilities),
            username=event.username,
            participant_id=event.participant_id,
        )
        if event.username and event.username.strip() and self.gemini_session_manager:
            self.gemini_session_manager.set_username(event.username.strip())
        if client.state.client_type == ClientType.HARDWARE:
            self._note_hardware_activity(keepalive=False)

        logger.info("\033[32m 🟢 Client %s (%s) registered.\033[0m", client.client_id, client.state.client_type)
        ack_event = RegistrationAckEvent(
            client_id=client.client_id,
            message=f"Successfully registered as {client.state.client_type}.",
            active_controller_id=None,
            current_active_controller_type=None,
            routing_config=None,
        )
        await client.send_event(ack_event)
        await self.broadcast(
            SystemMessageEvent(message=f"New {client.state.client_type} client ({client.client_id[:8]}) connected."),
            exclude_client_id=client.client_id,
        )

    async def broadcast(self, event, exclude_client_id: Optional[str] = None):
        for client_id, client in list(self.active_clients.items()):
            if client_id != exclude_client_id and client.state:
                await client.send_event(event)

    async def send_to_client(self, client_id: str, event):
        client = self.active_clients.get(client_id)
        if client:
            await client.send_event(event)
        else:
            logger.warning("Attempted to send event to non-existent client: %s", client_id)

    def get_client(self, client_id: str) -> Optional[WebSocketClient]:
        return self.active_clients.get(client_id)

    def get_clients_with_capability(self, capability: ClientCapability) -> Dict[str, WebSocketClient]:
        return {
            cid: client
            for cid, client in self.active_clients.items()
            if client.state and capability in client.state.capabilities
        }

    def get_preferred_frontend_client(self) -> Optional[WebSocketClient]:
        for client in self.active_clients.values():
            if client.state and client.state.client_type == ClientType.FRONTEND:
                return client
        return None

    def get_identity_client(self) -> Optional[WebSocketClient]:
        frontend_client = self.get_preferred_frontend_client()
        if frontend_client:
            return frontend_client
        for client in self.active_clients.values():
            if client.state:
                return client
        return None

    def get_clients_snapshot(self) -> list[dict]:
        snapshot = []
        for cid, client in self.active_clients.items():
            if not client.state:
                continue
            snapshot.append(
                {
                    "client_id": cid,
                    "client_type": getattr(client.state.client_type, "value", str(client.state.client_type)),
                    "capabilities": sorted([getattr(cap, "value", str(cap)) for cap in client.state.capabilities]),
                    "username": client.state.username,
                    "participant_id": client.state.participant_id,
                }
            )
        return snapshot

    def _note_hardware_activity(self, keepalive: bool = False) -> None:
        now = time.time()
        self._hardware_last_activity_ts = now
        if keepalive:
            self._hardware_last_keepalive_ts = now

    def get_hardware_status(self) -> dict:
        now = time.time()
        connected_hardware = [
            client
            for client in self.active_clients.values()
            if client.state and client.state.client_type == ClientType.HARDWARE
        ]
        connected = len(connected_hardware) > 0

        keepalive_age = None
        if self._hardware_last_keepalive_ts is not None:
            keepalive_age = max(0, int(now - self._hardware_last_keepalive_ts))

        if connected:
            if keepalive_age is not None:
                status_text = f"Prototype connected (last keepalive {keepalive_age}s ago)"
            else:
                status_text = "Prototype connected"
        else:
            if keepalive_age is not None:
                status_text = f"Prototype not connected (last keepalive {keepalive_age}s ago)"
            else:
                status_text = "Prototype not connected"

        return {
            "connected": connected,
            "connected_clients": len(connected_hardware),
            "last_keepalive_age_seconds": keepalive_age,
            "status_text": status_text,
        }

    async def start_event_processing(self):
        while True:
            client_id, event = await self.event_queue.get()
            try:
                if self.message_router:
                    await self.message_router(event, client_id)
                else:
                    logger.warning("WebSocketManager: message_router not set. Dropping event.")
            except Exception as e:
                logger.error("Error processing event from client %s: %s", client_id, e, exc_info=True)
            finally:
                self.event_queue.task_done()

    async def router_wrapper(self, event: IncomingEventType, client_id: str):
        client = self.get_client(client_id)
        if not client:
            logger.warning("Received event from unknown client %s. Dropping.", client_id)
            return

        if isinstance(event, RegisterEvent):
            await self.register_client(client, event)
            return

        if not client.state:
            if isinstance(event, KeepAliveEvent):
                client.set_state(
                    ClientType.HARDWARE,
                    {ClientCapability.SENSOR_INPUT},
                )
                self._note_hardware_activity(keepalive=True)
                logger.info(
                    "Client %s auto-provisioned as hardware keepalive client (stateless mode).",
                    client_id,
                )
                return

            if isinstance(event, SensorEvent):
                client.set_state(
                    ClientType.HARDWARE,
                    {ClientCapability.SENSOR_INPUT},
                )
                self._note_hardware_activity(keepalive=False)
                logger.info(
                    "Client %s auto-provisioned as hardware sensor client (stateless mode).",
                    client_id,
                )
            else:
                logger.warning(
                    "Client %s sent event '%s' before registration. Dropping.",
                    client_id,
                    event.type,
                )
                return

        if isinstance(event, KeepAliveEvent):
            if client.state and client.state.client_type == ClientType.HARDWARE:
                self._note_hardware_activity(keepalive=True)
            logger.debug("Received keepalive from client %s.", client_id)
            return

        if isinstance(event, SensorEvent):
            if client.state and client.state.client_type == ClientType.HARDWARE:
                self._note_hardware_activity(keepalive=False)

        if isinstance(event, SetActiveControllerEvent):
            await client.send_event(
                SystemMessageEvent(
                    message="Active controller switching is disabled. Inputs are routed by client capabilities."
                )
            )
            return

        if isinstance(event, RoutingConfigUpdateEvent):
            await client.send_event(
                SystemMessageEvent(
                    message="Routing config updates are disabled. Frontend audio/text and sensor capability rules are always active."
                )
            )
            return

        await self.event_queue.put((client_id, event))
