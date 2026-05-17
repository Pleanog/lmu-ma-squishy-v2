# FILE: app/tools/registry.py

# This file would typically contain custom ToolHandler classes or mappings
# if you had more complex tool logic that needed to be abstracted.
# For now, the ToolDispatcher directly handles the routing, but keeping
# the file for future expansion if per-tool registration becomes necessary.

import logging
from typing import Dict, Callable, Any, Optional, Type

logger = logging.getLogger(__name__)

# This could evolve into a more sophisticated registry
# For now, `app/gemini/tools.py` defines the schemas directly.
# The `ToolDispatcher` will use these schemas.

class ToolRegistry:
    def __init__(self):
        self._tool_handlers: Dict[str, Callable[..., Any]] = {}
        logger.info("ToolRegistry initialized.")

    def register_handler(self, tool_name: str, handler: Callable[..., Any]):
        """Registers a Python function as a handler for a specific tool."""
        if tool_name in self._tool_handlers:
            logger.warning(f"Tool handler for '{tool_name}' already registered. Overwriting.")
        self._tool_handlers[tool_name] = handler
        logger.debug(f"Registered handler for tool '{tool_name}'.")

    def get_handler(self, tool_name: str) -> Optional[Callable[..., Any]]:
        """Retrieves the handler for a given tool name."""
        return self._tool_handlers.get(tool_name)

# In this architecture, the GeminiSessionManager directly maps Gemini's tool calls
# to a _tool_call_wrapper, which then uses the ToolDispatcher.
# So, the ToolRegistry is currently less critical but is kept for architectural clarity
# and future extensibility where you might want more dynamic tool implementations.

tool_registry = ToolRegistry() # Singleton instance