import asyncio
import base64
import json
import logging
import os
import httpx # For PocketBase API interactions

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from gemini_live import GeminiLive
from tools.squishy_tools import squishy_tools

# --- PocketBase integration ---
# TODO: a more robust PocketBase client wrapper later
PB_URL = os.getenv("PB_URL")
PB_ADMIN_EMAIL = os.getenv("PB_ADMIN_EMAIL")
PB_ADMIN_PASS = os.getenv("PB_ADMIN_PASS")

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logging.getLogger("gemini_live").setLevel(logging.DEBUG) # Detailed Gemini Live logs
logging.getLogger(__name__).setLevel(logging.DEBUG) # FrontEnd App logs
logger = logging.getLogger(__name__)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-3.1-flash-live-preview")
# Initialize FastAPI
app = FastAPI(
    title="Squishy 2.0 Backend",
    description="FastAPI server for managing Gemini Live API, Squishy 2.0 hardware, and PocketBase logging.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global state or dependency injection for PocketBase client ---
# TODO: we want to initialize PocketBase once and reuse the client.
# For simplicity, we'll make a helper function here.
async def get_pb_admin_token():
    """Authenticates with PocketBase as admin and returns the token."""
    if not all([PB_URL, PB_ADMIN_EMAIL, PB_ADMIN_PASS]):
        logger.error("PocketBase credentials not fully set in .env")
        return None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PB_URL}/api/admins/auth-with-password",
                json={"identity": PB_ADMIN_EMAIL, "password": PB_ADMIN_PASS}
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

# --- Hardware WebSocket Endpoint for Squishy 2.0 ---
@app.websocket("/ws/hardware")
async def websocket_hardware_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for the Raspberry Pi (Squishy 2.0 hardware).
    Handles streaming audio from the ReSpeaker and sensor data from Squishy.
    Also sends actuator commands to Squishy.
    """
    await websocket.accept()
    logger.info("Hardware WebSocket connection accepted from Raspberry Pi")

    # Queues for data going to Gemini (from RPi)
    rpi_audio_input_queue = asyncio.Queue()
    rpi_sensor_input_queue = asyncio.Queue()

    # Queue for commands going to RPi (from Gemini tool calls)
    rpi_command_output_queue = asyncio.Queue()

    # --- Hardware-specific output callback for Gemini ---
    # This is where Gemini's tool calls will be processed and sent to the RPi
    async def squishy_actuator_callback(tool_name: str, args: dict):
        """
        Callback to send actuator commands to the Raspberry Pi.
        This function will be called by GeminiLive when a tool call occurs.
        """
        command = {"type": "tool_command", "tool_name": tool_name, "args": args}
        logger.debug(f"Putting command for RPi on queue: {command}")
        await rpi_command_output_queue.put(command)
    
    # --- Tool mapping to Python functions ---
    # These functions will be called when Gemini generates a tool call
    tool_mapping = {
        "set_led_color": lambda color: squishy_actuator_callback("set_led_color", {"color": color}),
        "play_squishy_sound": lambda sound_type: squishy_actuator_callback("play_squishy_sound", {"sound_type": sound_type}),
        "vibrate_squishy": lambda pattern: squishy_actuator_callback("vibrate_squishy", {"pattern": pattern}),
    }

    gemini_client_hardware = GeminiLive(
        api_key=GEMINI_API_KEY,
        model=MODEL,
        input_sample_rate=16000, # Assuming ReSpeaker provides 16kHz audio
        # tools=squishy_tools,
        # tool_mapping=tool_mapping
    )

    async def receive_from_rpi():
        """Handles incoming messages from the Raspberry Pi."""
        try:
            while True:
                message = await websocket.receive()
                if message.get("bytes"):
                    # Raw audio from ReSpeaker
                    await rpi_audio_input_queue.put(message["bytes"])
                elif message.get("text"):
                    # Structured sensor data or other RPi messages (JSON)
                    text_data = message["text"]
                    try:
                        payload = json.loads(text_data)
                        if isinstance(payload, dict) and payload.get("type") == "sensor_event":
                            logger.info(f"Received sensor event from RPi: {payload}")
                            # Convert sensor event to text for Gemini, e.g., "System: User is petting Squishy."
                            # You can refine this translation based on your needs.
                            await rpi_sensor_input_queue.put(
                                f"System: User {payload['event']} Squishy with {payload.get('intensity', 'unknown')} intensity."
                            )
                        else:
                            # Handle other text messages from RPi if any
                            logger.info(f"Received unexpected text from RPi: {text_data}")
                            await rpi_sensor_input_queue.put(text_data) # Or put to another queue
                    except json.JSONDecodeError:
                        logger.warning(f"RPi sent non-JSON text: {text_data}")
                        await rpi_sensor_input_queue.put(text_data)
        except WebSocketDisconnect:
            logger.info("Hardware WebSocket disconnected from Raspberry Pi")
        except Exception as e:
            logger.error(f"Error receiving from RPi: {e}", exc_info=True)

    async def send_to_rpi():
        """Sends commands from FastAPI (via Gemini tool calls) to the Raspberry Pi."""
        try:
            while True:
                command = await rpi_command_output_queue.get()
                logger.debug(f"Sending command to RPi: {command}")
                await websocket.send_json(command)
        except asyncio.CancelledError:
            logger.debug("send_to_rpi task cancelled")
        except Exception as e:
            logger.error(f"Error sending to RPi: {e}", exc_info=True)

    receive_from_rpi_task = asyncio.create_task(receive_from_rpi())
    send_to_rpi_task = asyncio.create_task(send_to_rpi())

    async def run_hardware_session():
        """Main loop for the RPi's Gemini session."""
        async for event in gemini_client_hardware.start_session(
            audio_input_queue=rpi_audio_input_queue,
            video_input_queue=asyncio.Queue(), # RPi doesn't send video for now
            text_input_queue=rpi_sensor_input_queue, # Sensor data translated to text
            audio_output_callback=lambda data: None, # RPi doesn't play AI voice directly
                                                    # AI voice goes to frontend's ws
        ):
            if event:
                # Process events from Gemini (transcriptions etc.) specific to RPi's session
                logger.debug(f"Gemini event from RPi session: {event}")
                # Log this event to PocketBase or forward to frontend for display
                # (You'll integrate PocketBase logging here later)
                pass # For now, just log and ignore


    try:
        await run_hardware_session()
    except Exception as e:
        logger.error(f"Error in Gemini session for RPi: {type(e).__name__}: {e}", exc_info=True)
    finally:
        receive_from_rpi_task.cancel()
        send_to_rpi_task.cancel()
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for the Vue.js Frontend (Companion App).
    Handles user's browser microphone audio and displays AI responses.
    This will also receive updates about Squishy's actions.
    """
    await websocket.accept()

    logger.info("Frontend WebSocket connection accepted")

    audio_input_queue = asyncio.Queue()  # For browser mic audio
    video_input_queue = asyncio.Queue()  # For browser camera video (if you add it)
    text_input_queue = asyncio.Queue()   # For browser text input (if you add it)

    # Use an Event to signal tasks to stop if disconnect occurs
    disconnect_event = asyncio.Event()

    # --- Frontend-specific output callback for Gemini ---
    async def audio_output_callback(data):
        if not disconnect_event.is_set(): # Only try to send if not disconnected
            try:
                await websocket.send_bytes(data)
            except RuntimeError as e:
                logger.warning(f"Failed to send audio bytes to frontend (likely disconnected): {e}")
                disconnect_event.set() # Set event if send fails

    async def audio_interrupt_callback():
        if not disconnect_event.is_set(): # Only try to send if not disconnected
            try:
                await websocket.send_json({"type": "interrupted"})
            except RuntimeError as e:
                logger.warning(f"Failed to send audio interrupt to frontend (likely disconnected): {e}")
                disconnect_event.set() # Set event if send fails


    gemini_client_frontend = GeminiLive(
        api_key=GEMINI_API_KEY,
        model=MODEL,
        input_sample_rate=16000, # Assuming browser mic provides 16kHz audio
        # tools=... # Frontend's Gemini session typically doesn't need to define tools
        # audio_output_callback=audio_output_callback,
        # audio_interrupt_callback=audio_interrupt_callback,
    )

    async def receive_from_client():
        """Handles incoming messages (audio, text, video) from the frontend."""
        try:
            while not disconnect_event.is_set(): # Loop while not disconnected
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    logger.info("Frontend WebSocket detected disconnect.")
                    disconnect_event.set() # Signal disconnect
                    break # Exit loop
                # Process other message types
                if message.get("bytes"):
                    await audio_input_queue.put(message["bytes"])
                elif message.get("text"):
                    text = message["text"]
                    try:
                        payload = json.loads(text)
                        if isinstance(payload, dict) and payload.get("type") == "image":
                            logger.info(f"Received image chunk from client: {len(payload['data'])} base64 chars")
                            image_data = base64.b64decode(payload["data"])
                            await video_input_queue.put(image_data)
                            continue
                    except json.JSONDecodeError:
                        pass

                    await text_input_queue.put(text)
        except WebSocketDisconnect:
            logger.info("Frontend WebSocket disconnected gracefully (from exception).")
            disconnect_event.set() # Signal disconnect
        except Exception as e:
            logger.error(f"Error receiving from frontend client: {e}", exc_info=True)
            disconnect_event.set() # Signal disconnect on any error

    async def run_frontend_session():
        """Main loop for the frontend's Gemini session."""
        try:
            async for event in gemini_client_frontend.start_session(
                audio_input_queue=audio_input_queue,
                video_input_queue=video_input_queue,
                text_input_queue=text_input_queue,
                audio_output_callback=audio_output_callback,
                audio_interrupt_callback=audio_interrupt_callback, 
                # audio_output_callback and audio_interrupt_callback are set during GeminiLive init
            ):
                if disconnect_event.is_set(): # If client disconnected, stop processing Gemini events
                    logger.debug("Client disconnected, stopping Gemini event processing.")
                    break
                if event:
                    # Forward events (transcriptions, etc.) to the frontend
                    try:
                        await websocket.send_json(event)
                    except RuntimeError as e:
                        logger.warning(f"Failed to send Gemini event to frontend (likely disconnected): {e}")
                        disconnect_event.set() # Set event if send fails
                        break # Exit loop as client is gone
        except asyncio.CancelledError:
            logger.info("Gemini frontend session task cancelled.")
        except Exception as e:
            logger.error(f"Error in Gemini session for frontend: {type(e).__name__}: {e}", exc_info=True)
        finally:
            logger.debug("run_frontend_session finished or interrupted.")
            disconnect_event.set() # Ensure event is set if this task finishes first

    # Create tasks
    receive_from_frontend_task = asyncio.create_task(receive_from_client())
    run_frontend_session_task = asyncio.create_task(run_frontend_session())
    # Create a task for the event.wait() coroutine
    disconnect_wait_task = asyncio.create_task(disconnect_event.wait())

    # Wait for either task to signal disconnect or complete
    done, pending = await asyncio.wait(
        [receive_from_frontend_task, run_frontend_session_task, disconnect_wait_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    # If disconnect_event.wait() completed, ensure other tasks are cancelled
    if disconnect_event.is_set():
        for task in pending:
            task.cancel()
            try:
                await task # Await cancellation to avoid Task exception was never retrieved warnings
            except asyncio.CancelledError:
                pass

    logger.info("Frontend WebSocket endpoint shutting down.")

    # Final websocket close (redundant if already closed by Starlette, but safe)
    try:
        if not websocket.client_state == 3: # WebSocketState.DISCONNECTED
             await websocket.close()
    except Exception as e:
        logger.debug(f"Error during final websocket close (may already be closed): {e}")


# --- Main execution block ---
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    # It's good practice to run Uvicorn with a server factory or programmatically
    # to better manage application state if you had more complex setups.
    # For now, this is fine.
    uvicorn.run(app, host="0.0.0.0", port=port)