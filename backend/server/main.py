# FILE: app/main.py

import asyncio
import logging
import colorlog
import httpx # For PocketBase API interactions
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

from config import settings
from websocket.manager import WebSocketManager
from websocket.router import MessageRouter
from gemini.session import GeminiSessionManager
from tools.dispatcher import ToolDispatcher
from tools.squishy_tools import squishy_tools # The actual tool definitions
from models.events import ErrorEvent, SystemMessageEvent
from interaction_logger import PocketBaseInteractionLogger
from memory_store import PocketBaseMemoryStore

# --- Logging Setup ---
console_handler = colorlog.StreamHandler()
console_handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s "
        "\033[90m%(name)s\033[0m: "
        "%(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
)

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

# Configure root logger
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(console_handler)
root_logger.setLevel(logging.INFO)

# Configure specific logger levels
logging.getLogger("gemini_live").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Logger for this file
logger = logging.getLogger(__name__)

# --- Global State / Dependency Injection Containers ---
ws_manager: WebSocketManager
tool_dispatcher: ToolDispatcher
gemini_session_manager: GeminiSessionManager
message_router: MessageRouter
memory_store: PocketBaseMemoryStore
interaction_logger: PocketBaseInteractionLogger

async def get_pb_admin_token():
    """Authenticates with PocketBase as admin and returns the token."""
    if not all([settings.PB_URL, settings.PB_ADMIN_EMAIL, settings.PB_ADMIN_PASS]):
        logger.error("PocketBase credentials not fully set in .env")
        return None
    try:
        async with httpx.AsyncClient() as client:
            auth_payload = {"identity": settings.PB_ADMIN_EMAIL, "password": settings.PB_ADMIN_PASS}
            response = await client.post(
                f"{settings.PB_URL}/api/collections/_superusers/auth-with-password",
                json=auth_payload,
            )
            if response.status_code == 404:
                response = await client.post(
                    f"{settings.PB_URL}/api/admins/auth-with-password",
                    json=auth_payload
                )
            response.raise_for_status()
            token = response.json()["token"]
            logger.info("Successfully authenticated with PocketBase as admin.")
            return token
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to authenticate with PocketBase: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error connecting to PocketBase: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.
    Initializes global services.
    """
    global ws_manager, tool_dispatcher, gemini_session_manager, message_router, memory_store, interaction_logger
    
    logger.info(GREEN + "Starting Squishy 2.0 Backend Server" + RESET)

    memory_store = PocketBaseMemoryStore(
        pb_url=settings.PB_URL,
        admin_email=settings.PB_ADMIN_EMAIL,
        admin_password=settings.PB_ADMIN_PASS,
        collection_name="saved_memories",
    )
    interaction_logger = PocketBaseInteractionLogger(
        pb_url=settings.PB_URL,
        admin_email=settings.PB_ADMIN_EMAIL,
        admin_password=settings.PB_ADMIN_PASS,
        collection_name="interaction_logs",
    )

    # 1. Initialize WebSocket Manager
    ws_manager = WebSocketManager()

    # 2. Initialize Tool Dispatcher and register tools
    tool_dispatcher = ToolDispatcher(ws_manager)
    tool_dispatcher.register_tool_schemas(squishy_tools)

    # 3. Initialize Gemini Session Manager
    gemini_session_manager = GeminiSessionManager(
        ws_manager,
        tool_dispatcher,
        memory_store=memory_store,
        interaction_logger=interaction_logger,
    )
    ws_manager.gemini_session_manager = gemini_session_manager
    await gemini_session_manager.initialize_gemini_client() # Pre-initialize GeminiLive

    # 4. Initialize Message Router (connects all services)
    message_router = MessageRouter(ws_manager, gemini_session_manager, tool_dispatcher)
    # The ws_manager.message_router is set within the MessageRouter's __init__

    # Start background tasks
    asyncio.create_task(ws_manager.start_event_processing())
    # asyncio.create_task(gemini_session_manager.start_session()) # Start Gemini session loop manuell on startup, aber Session selbst startet jetzt on demand

    # Authenticate with PocketBase on startup
    pb_token = await get_pb_admin_token()
    if pb_token:
        logger.info(GREEN + "PocketBase admin token acquired." + RESET)
        # Store token globally if needed, or pass to a PocketBase client instance
    else:
        logger.warning(ORANGE + "Could not acquire PocketBase admin token on startup." + RESET)

    logger.info(GREEN + "Squishy 2.0 Backend startup complete." + RESET)
    logger.info(CYAN + "Gemini session will start on demand." + RESET)

    yield
    logger.info("Shutting down Squishy 2.0 Backend...")
    logger.info(ORANGE + "Stopping Gemini session..." + RESET)
    await gemini_session_manager.stop_session()
    logger.info(GREEN + "Squishy 2.0 Backend shutdown complete." + RESET)


app = FastAPI(
    title="Squishy 2.0 Backend",
    description="FastAPI server for managing Gemini Live API, Squishy 2.0 hardware, and PocketBase logging.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SaveMemoryRequest(BaseModel):
    participant_id: str
    content: str
    username: Optional[str] = None
    source: str = "server_manual"
    trigger_event: Optional[str] = None


@app.get("/api/interactions")
async def list_interactions(participant_id: str = Query(..., min_length=1)):
    try:
        return {
            "items": await interaction_logger.list_interactions(participant_id=participant_id.strip()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list interactions: {e}")


@app.get("/api/memories")
async def list_memories(participant_id: str = Query(..., min_length=1)):
    try:
        return {
            "items": await memory_store.list_memories(participant_id=participant_id.strip()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {e}")


@app.post("/api/memories/save")
async def save_memory(request: SaveMemoryRequest):
    try:
        item = await memory_store.save_memory(
            participant_id=request.participant_id.strip(),
            username=(request.username or "").strip() or "Server",
            content=request.content.strip(),
            source=request.source,
            trigger_event=request.trigger_event,
        )
        return {"item": item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save memory: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Unified WebSocket endpoint for all clients (frontend, hardware, monitor).
    Clients must register themselves upon connection.
    """
    client = await ws_manager.connect(websocket)
    try:
        async for event in client.receive_events():
            # All incoming events go through the WebSocketManager's router_wrapper first
            # which handles registration and active controller requests, then puts
            # other events into the main event_queue for the MessageRouter.
            await ws_manager.router_wrapper(event, client.client_id)
    except WebSocketDisconnect:
        logger.info(f"Client {client.client_id} disconnected from /ws.")
    except Exception as e:
        logger.error(f"Error in WebSocket communication for client {client.client_id}: {e}", exc_info=True)
        # Send an error event to the client before disconnecting, if possible
        try:
            await client.send_event(ErrorEvent(message=f"Server error: {e.__class__.__name__}"))
        except Exception:
            pass # Ignore if client already unreachable
    finally:
        await ws_manager.disconnect(client.client_id)
        logger.info(f"Client {client.client_id} fully cleaned up.")


if __name__ == "__main__":
    import uvicorn
    port = int(settings.PORT if hasattr(settings, 'PORT') else 8000)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True) # reload=True for development