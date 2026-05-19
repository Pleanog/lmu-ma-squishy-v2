import asyncio
import logging
import sys
from typing import Union, Dict, Any
from client.websocket_client import WebSocketClient, IncomingBackendJsonEvent, RegistrationAckEvent, AIResponseEvent, ToolCallEvent, TranscriptEvent
from client.audio_handler import AudioHandler
from config import BACKEND_WS_URL, CLIENT_CAPABILITIES

logging.basicConfig(level=logging.INFO, stream=sys.stdout, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# audio_handler = AudioHandler(samplerate=24000, channels=1, dtype='int16')
audio_handler = AudioHandler(hardware_samplerate=48000, channels=2, dtype='float32', volume_factor=1.0)

def on_connect():
    logger.info("Successfully connected to the backend!")

def on_error(e: Exception):
    logger.error(f"WebSocket error occurred: {e}")

async def handle_backend_message(data: Union[IncomingBackendJsonEvent, bytes]):
    if isinstance(data, bytes):
        logger.debug(f"Received {len(data)} bytes of audio data. Playing...")      
        audio_handler.play_audio(data, incoming_samplerate=24000)
    elif isinstance(data, dict):
        message_type = data.get("type")
        if message_type == "registration_ack":
            ack_data: RegistrationAckEvent = data
            logger.info(f"Registration acknowledged: {ack_data.get('message')}")
        elif message_type == "ai_response":
            ai_response: AIResponseEvent = data
            logger.info(f"AI Response (Text): {ai_response.get('text')}")
        elif message_type == "transcript":
            transcript_data: TranscriptEvent = data
            logger.info(f"Transcript ({'Final' if transcript_data.get('is_final') else 'Interim'}): {transcript_data.get('text')}")
        elif message_type == "tool_call":
            tool_call_data: ToolCallEvent = data
            tool_name = tool_call_data.get('tool_name')
            tool_args = tool_call_data.get('args')
            suggested_action = tool_call_data.get('suggested_action')
            logger.info(f"TOOL CALL: {tool_name}({tool_args}) - Suggested Action: {suggested_action}")
            await simulate_tool_call(tool_name, tool_args, suggested_action)
        elif message_type == "system_message":
            logger.info(f"System Message: {data.get('message')}")
        elif message_type == "error":
            logger.error(f"Backend Error: {data.get('message')}")
        else:
            logger.info(f"Received unknown JSON message: {data}")
    else:
        logger.warning(f"Received unexpected message format: {type(data)} - {data}")

async def simulate_tool_call(tool_name: str, args: Dict[str, Any], suggested_action: str):
    logger.info(f"Simulating Tool Call: {tool_name} with args {args} and action '{suggested_action}'")
    
    if tool_name == "set_led_color":
        color = args.get("color", "unknown")
        duration = args.get("duration_seconds", 1)
        logger.info(f"  -> Simulating: Set LED color to {color} for {duration} seconds.")
    elif tool_name == "play_sound_effect":
        effect_name = args.get("effect_name", "beep")
        logger.info(f"  -> Simulating: Play sound effect '{effect_name}'.")
        print(f"  [Sound Effect: {effect_name}]")
    elif tool_name == "get_sensor_data":
        sensor_type = args.get("sensor_type", "temperature")
        logger.info(f"  -> Simulating: Get data from {sensor_type} sensor.")
        print(f"  [Sensor Reading: {sensor_type} = 25.0 C (simulated)]")
    else:
        logger.warning(f"  -> Unknown tool call simulation for '{tool_name}'.")

# Diese Funktion kapselt den blockierenden input()-Aufruf
def get_user_input_blocking():
    return input("Enter message (or 'exit' to quit): ")

async def main():
    logger.info("Starting Squishy Pi Client.")

    websocket_client = WebSocketClient(
        ws_url=BACKEND_WS_URL,
        client_type="hardware",
        capabilities=CLIENT_CAPABILITIES,
        on_message_callback=handle_backend_message,
        on_connect_callback=on_connect,
        on_error_callback=on_error
    )

    await websocket_client.connect()
    await asyncio.sleep(2) 

    if websocket_client.is_connected:
        logger.info(f"Current active controller ID: {websocket_client.active_controller_id}")
        logger.info(f"My client ID: {websocket_client.client_id}")

        if websocket_client.client_id and websocket_client.client_id == websocket_client.active_controller_id:
            logger.info("I am the active controller. Initiating persona greeting.")
            await websocket_client.send_text_message("Sag einmal nur das Wort Apfelbaum")
        else:
            logger.warning("I am not the active controller. Requesting control...")
            await websocket_client.request_set_active_controller()
            await asyncio.sleep(1)
            if websocket_client.client_id == websocket_client.active_controller_id:
                logger.info("Successfully became the active controller! Initiating persona greeting.")
                await websocket_client.send_text_message("Sag einmal nur das Wort Pferdestall")
            else:
                logger.warning("Failed to become active controller. I can only listen.")


        # Schleife zum Senden von Text vom Pi an Gemini, jetzt nicht-blockierend
        while websocket_client.is_connected:
            # Führe den blockierenden input-Aufruf in einem separaten Thread aus
            user_input = await asyncio.to_thread(get_user_input_blocking)
            
            if user_input.lower() == 'exit':
                break
            if websocket_client.client_id == websocket_client.active_controller_id:
                await websocket_client.send_text_message(user_input)
            else:
                logger.warning("Cannot send message, I am not the active controller.")
    else:
        logger.error("Failed to connect to WebSocket, exiting.")

    await websocket_client.disconnect()
    audio_handler.stop_playback()
    logger.info("Squishy Pi Client stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("An unexpected error occurred in main.")