# FILE: app/tools/dispatcher.py

import asyncio
import logging
from typing import Any, List
from google.genai import types

from models.events import ToolCallEvent, ErrorEvent
from websocket.manager import WebSocketManager # type: ignore
from models.client_state import ClientCapability

logger = logging.getLogger(__name__)

class ToolDispatcher:
    """
    Dispatches tool calls from Gemini to relevant clients based on their capabilities.
    Also handles collecting tool responses and sending them back to the Gemini session.
    """
    def __init__(self, ws_manager: 'WebSocketManager'):
        self.ws_manager = ws_manager
        self._registered_tool_schemas: List[types.Tool] = []
        logger.info("ToolDispatcher initialized.")

    def register_tool_schemas(self, tool_schemas: List[types.Tool]):
        """Registers the tool schemas that Gemini can use."""
        self._registered_tool_schemas.extend(tool_schemas)
        logger.info(f"Registered {len(tool_schemas)} tool schemas.")

    def get_all_tool_schemas(self) -> List[types.Tool]:
        """Returns all registered tool schemas."""
        return self._registered_tool_schemas

    async def dispatch_tool_call(self, tool_call_event: ToolCallEvent):
        """
        Dispatches a tool call event to clients.
        Clients decide based on capabilities whether to execute, simulate, or visualize.
        """
        tool_name = tool_call_event.tool_name
        tool_call_id = tool_call_event.tool_call_id
        args = tool_call_event.args

        logger.info(f"Dispatching tool call '{tool_name}' (ID: {tool_call_id}) with args: {args}")

        dispatched_to_any_client = False
        send_tasks = []

        # Find clients capable of executing the tool.
        executing_clients = self.ws_manager.get_clients_with_capability(ClientCapability.TOOL_EXECUTION)
        if executing_clients:
            logger.debug(f"Tool '{tool_name}' can be executed by: {list(executing_clients.keys())}")
            for client_id, client in executing_clients.items():
                event_for_client = tool_call_event.model_copy(update={"suggested_action": "execute"})
                send_tasks.append(client.send_event(event_for_client))
                dispatched_to_any_client = True
                logger.debug(f"Sending '{tool_name}' to client {client_id} for EXECUTION.")
        
        # Find clients capable of visualizing/simulating the tool (e.g., frontend)
        visualizing_clients = self.ws_manager.get_clients_with_capability(ClientCapability.TOOL_VISUALIZATION)
        simulating_clients = self.ws_manager.get_clients_with_capability(ClientCapability.TOOL_SIMULATION)

        # Ensure all capable clients receive the event, even if not executing
        for client_id, client in self.ws_manager.active_clients.items():
            if client.state and client_id not in executing_clients: # Avoid double-sending to executing clients
                if ClientCapability.TOOL_VISUALIZATION in client.state.capabilities:
                    event_for_client = tool_call_event.model_copy(update={"suggested_action": "visualize"})
                    send_tasks.append(client.send_event(event_for_client))
                    dispatched_to_any_client = True
                    logger.debug(f"Sending '{tool_name}' to client {client_id} for VISUALIZATION.")
                elif ClientCapability.TOOL_SIMULATION in client.state.capabilities:
                    # A client might simulate if it's the active controller but lacks execution, or for debugging
                    event_for_client = tool_call_event.model_copy(update={"suggested_action": "simulate"})
                    send_tasks.append(client.send_event(event_for_client))
                    dispatched_to_any_client = True
                    logger.debug(f"Sending '{tool_name}' to client {client_id} for SIMULATION.")


        if send_tasks:
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error sending tool call to client: {result}")
        
        if not dispatched_to_any_client:
            logger.warning(f"No clients found with capabilities to handle tool call '{tool_name}' (ID: {tool_call_id}).")
            # If no client can handle, send an error response back to Gemini
            frontend_client = self.ws_manager.get_preferred_frontend_client()
            if frontend_client:
                await self.ws_manager.send_to_client(
                    frontend_client.client_id,
                    ErrorEvent(message=f"No client could handle tool call '{tool_name}'.")
                )
            # Send an explicit error response to Gemini
            # This is critical for Gemini to continue if a tool fails to execute
            if self.ws_manager.gemini_session_manager:
                await self.ws_manager.gemini_session_manager.tool_response_queue.put(
                    (tool_call_id, tool_name, {"result": "error", "message": f"No client capable of handling tool '{tool_name}'."})
                )