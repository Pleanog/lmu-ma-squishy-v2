# FILE: app/websocket/manager.py

import asyncio
import logging
from typing import Any, Coroutine, Dict, Optional, Set, AsyncGenerator, Callable
from uuid import uuid4

from fastapi import WebSocket

from websocket.client import WebSocketClient
from models.client_state import ClientType, ClientCapability
from models.events import (
    IncomingEventType, RegisterEvent, RegistrationAckEvent,
    ActiveControllerChangeEvent, OutgoingEventType, ErrorEvent,
    SetActiveControllerEvent, SystemMessageEvent
)

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages all active WebSocket connections, client registration,
    and active controller logic.
    """
    def __init__(self):
        self.active_clients: Dict[str, WebSocketClient] = {}
        self.active_controller_id: Optional[str] = None
        self.event_queue: asyncio.Queue[tuple[str, IncomingEventType]] = asyncio.Queue() # Store (client_id, event) tuples
        self.message_router: Optional[Callable[[IncomingEventType, str], Coroutine[Any, Any, None]]] = None # Will be set by main.py
        logger.info("WebSocketManager initialized.")

    async def connect(self, websocket: WebSocket) -> WebSocketClient:
        """Handles a new WebSocket connection, creates a client, and waits for registration."""
        client = WebSocketClient(websocket)
        await client.accept()
        self.active_clients[client.client_id] = client
        logger.info(f"Client {client.client_id} connected. Total active clients: {len(self.active_clients)}")
        await asyncio.sleep(0) # Yield control to allow client's _send_task to start
        return client

    async def disconnect(self, client_id: str):
        """Removes a client from the manager and handles active controller transfer."""
        client = self.active_clients.pop(client_id, None)
        if client:
            logger.info(f"Client {client_id} disconnected. Total active clients: {len(self.active_clients)}")
            # client.disconnect() is now managed internally by the client itself,
            # or initiated from its own loops. Just ensure it's removed from manager.
            if self.active_controller_id == client_id:
                logger.info(f"Active controller {client_id} disconnected. Electing new active controller...")
                self.active_controller_id = None
                await self._elect_new_active_controller()
            await self.broadcast(SystemMessageEvent(message=f"{client.state.client_type if client.state else 'Unknown'} client ({client.client_id[:8]}) disconnected."))

        else:
            logger.warning(f"Attempted to disconnect non-existent client: {client_id}")

    async def register_client(self, client: WebSocketClient, event: RegisterEvent):
        """Registers a client with its type and capabilities."""
        if client.state:
            logger.warning(f"Client {client.client_id} already registered. Ignoring re-registration.")
            await client.send_event(ErrorEvent(message="Client already registered."))
            return

        client.set_state(event.client_type, set(event.capabilities))
        logger.info(f"Client {client.client_id} ({client.state.client_type}) registered.")

        # If no active controller, or if this client can be active and requests it implicitly
        if not self.active_controller_id and client.state.capabilities.intersection(
            {ClientCapability.AUDIO_INPUT, ClientCapability.TEXT_INPUT}
        ):
            await self.set_active_controller(client.client_id)
            logger.info(f"Client {client.client_id} automatically set as active controller.")

        ack_event = RegistrationAckEvent(
            client_id=client.client_id,
            message=f"Successfully registered as {client.state.client_type}.",
            active_controller_id=self.active_controller_id,
            current_active_controller_type=self.active_clients[self.active_controller_id].state.client_type if self.active_controller_id and self.active_clients.get(self.active_controller_id) else None
        )
        await client.send_event(ack_event)
        await self.broadcast(SystemMessageEvent(message=f"New {client.state.client_type} client ({client.client_id[:8]}) connected."), exclude_client_id=client.client_id)


    async def set_active_controller(self, client_id: str) -> bool:
        """
        Sets the specified client as the active controller.
        Returns True if successful, False otherwise.
        """
        new_active_client = self.active_clients.get(client_id)
        if not new_active_client or not new_active_client.state:
            logger.warning(f"Cannot set {client_id} as active controller: Client not found or not registered.")
            return False

        if not new_active_client.state.capabilities.intersection(
            {ClientCapability.AUDIO_INPUT, ClientCapability.TEXT_INPUT}
        ):
            logger.warning(f"Client {client_id} does not have capabilities to be an active controller.")
            await new_active_client.send_event(ErrorEvent(message="Client lacks capabilities to be active controller."))
            return False

        old_active_controller_id = self.active_controller_id
        old_active_controller_type = None
        if old_active_controller_id and old_active_controller_id != client_id:
            old_active_client = self.active_clients.get(old_active_controller_id)
            if old_active_client and old_active_client.state:
                old_active_controller_type = old_active_client.state.client_type
            logger.info(f"Active controller changed from {old_active_controller_id} to {client_id}.")
            
        self.active_controller_id = client_id
        new_active_controller_type = new_active_client.state.client_type

        change_event = ActiveControllerChangeEvent(
            new_active_controller_id=client_id,
            new_active_controller_type=new_active_controller_type,
            old_active_controller_id=old_active_controller_id,
            old_active_controller_type=old_active_controller_type
        )
        await self.broadcast(change_event)
        await self.broadcast(SystemMessageEvent(message=f"{new_active_controller_type} client ({new_active_client.client_id[:8]}) is now the active controller."))
        return True

    async def _elect_new_active_controller(self):
        """Tries to elect a new active controller if the current one disconnects."""
        # Prioritize hardware if available and capable
        for client_id, client in list(self.active_clients.items()): # Iterate on a copy
            if client.state and client.state.client_type == ClientType.HARDWARE and \
               client.state.capabilities.intersection({ClientCapability.AUDIO_INPUT, ClientCapability.TEXT_INPUT}):
                await self.set_active_controller(client_id)
                return

        # Otherwise, prioritize frontend if available and capable
        for client_id, client in list(self.active_clients.items()): # Iterate on a copy
            if client.state and client.state.client_type == ClientType.FRONTEND and \
               client.state.capabilities.intersection({ClientCapability.AUDIO_INPUT, ClientCapability.TEXT_INPUT}):
                await self.set_active_controller(client_id)
                return

        logger.info("No suitable client found to become the active controller.")
        await self.broadcast(SystemMessageEvent(message="No active controller currently assigned."))


    async def broadcast(self, event: OutgoingEventType, exclude_client_id: Optional[str] = None):
        """Sends an event to all registered clients."""
        # These are coroutines that put messages on each client's internal queue.
        # Exceptions within the client's _send_loop are handled there.
        # We don't await/gather here to check individual task exceptions.
        # Just ensure the send_event call is initiated for all.
        for client_id, client in list(self.active_clients.items()): # Use list to avoid RuntimeError if dict changes
            if client_id != exclude_client_id and client.state:
                # Fire and forget into the client's queue.
                # The client's _send_loop is responsible for actual sending and error handling.
                await client.send_event(event) # Simply await the put operation

    async def send_to_client(self, client_id: str, event: OutgoingEventType):
        """Sends an event to a specific client."""
        client = self.active_clients.get(client_id)
        if client:
            await client.send_event(event)
        else:
            logger.warning(f"Attempted to send event to non-existent client: {client_id}")

    def get_client(self, client_id: str) -> Optional[WebSocketClient]:
        """Retrieves a client by its ID."""
        return self.active_clients.get(client_id)

    def get_active_controller(self) -> Optional[WebSocketClient]:
        """Returns the currently active controller client."""
        if self.active_controller_id:
            return self.active_clients.get(self.active_controller_id)
        return None
    
    # def get_active_controller(self) -> Optional[WebSocketClient]:
    #     """Gibt das WebSocketClient-Objekt des aktiven Controllers zurück."""
    #     if self.active_controller_id and self.active_controller_id in self.active_clients:
    #         return self.active_clients[self.active_controller_id]
    #     return None

    def get_clients_with_capability(self, capability: ClientCapability) -> Dict[str, WebSocketClient]:
        """Returns clients that possess a given capability."""
        return {
            cid: client
            for cid, client in self.active_clients.items()
            if client.state and capability in client.state.capabilities
        }

    async def start_event_processing(self):
        """Main loop for processing events from all connected clients."""
        while True:
            client_id, event = await self.event_queue.get()
            try:
                if self.message_router:
                    await self.message_router(event, client_id)
                else:
                    logger.warning("WebSocketManager: message_router not set. Dropping event.")
            except Exception as e:
                logger.error(f"Error processing event from client {client_id}: {e}", exc_info=True)
            finally:
                self.event_queue.task_done()

    async def router_wrapper(self, event: IncomingEventType, client_id: str):
        """
        This wrapper is called by the message_router and handles basic event routing
        like registration and active controller changes before passing to the main router.
        """
        client = self.get_client(client_id)
        if not client:
            logger.warning(f"Received event from unknown client {client_id}. Dropping.")
            return

        # Crucial: Handle RegisterEvent *first* and ensure client state is set
        if isinstance(event, RegisterEvent):
            await self.register_client(client, event)
            return # Registration handled, do not pass to main router

        # For any other event, if client is not yet registered, send error and drop
        if not client.state:
            logger.warning(f"Client {client_id} sent event '{event.type}' before registration. Sending error and dropping.")
            await client.send_event(ErrorEvent(message="Please register first."))
            return

        if isinstance(event, SetActiveControllerEvent):
            if event.client_id == client_id: # Only allow client to request itself as active controller
                await self.set_active_controller(client_id)
            else:
                logger.warning(f"Client {client_id} tried to set {event.client_id} as active controller.")
                await client.send_event(ErrorEvent(message="You can only request to set yourself as the active controller."))
            return # Active controller change handled, do not pass to main router

        # All other events are put into the main event queue for Gemini and tool dispatching
        await self.event_queue.put((client_id, event))