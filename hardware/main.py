import asyncio
import logging
import sys
import json # Für json.dumps im Tool Call Logging
from typing import Union, Dict, Any, Optional
from client.websocket_client import (
    WebSocketClient,
    AllIncomingJsonEvents,
    RegistrationAckEvent,
    ActiveControllerChangeEvent,
    AIResponseEvent,
    ToolCallEvent,
    TranscriptEvent,
    SystemMessageEvent,
    ErrorEvent,
)
from client.audio_handler import AudioHandler
from client.audio_input_handler import AudioInputHandler
from client.hardware_handler import HardwareHandler

from config import BACKEND_WS_URL, CLIENT_CAPABILITIES

logging.basicConfig(level=logging.INFO, stream=sys.stdout, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialisiere den Audio-Output-Handler (für Sprachausgabe vom Backend)
audio_output_handler = AudioHandler(hardware_samplerate=48000, channels=2, dtype='float32', volume_factor=1.0)
audio_playback_queue = asyncio.Queue()

async def audio_playback_worker():
    while True:
        # Wartet, bis neue Audiodaten in der Queue landen
        data = await audio_playback_queue.get()
        
        if data is None: # Abbruchsignal beim Beenden des Programms
            break
            
        # Führt die blockierende Play-Funktion in einem separaten Thread aus!
        await asyncio.to_thread(audio_output_handler.play_audio, data, 24000)
        
        # Sagt der Queue, dass dieser Chunk fertig ist
        audio_playback_queue.task_done()

async def send_sensor_data_to_gemini(text_message: str):
    """Wird vom HardwareHandler gerufen, wenn ein Sensor anschlägt."""
    if websocket_client and websocket_client.is_connected:
        logger.info(f"Sende Sensor-Kontext an KI: {text_message}")
        await websocket_client.send_text_message(text_message)

async def handle_tool_call(tool_name: str, args: Dict[str, Any], suggested_action: str):
    logger.info(f"⚙️ TOOL CALL vom Server empfangen: {tool_name}")
    hardware_handler.handle_tool_call(tool_name, args)

# Globale Instanzen
websocket_client: Optional[WebSocketClient] = None
audio_input_handler: Optional[AudioInputHandler] = None

# Callback für eingehende Audio-Daten vom Mikrofon zum WebSocket
async def send_recorded_audio_to_websocket(audio_bytes: bytes):
    """
    Diese Funktion wird vom AudioInputHandler aufgerufen, wenn neue Audio-Daten verfügbar sind.
    Sie sendet die Daten direkt an den WebSocketClient, wenn dieser der aktive Controller ist.
    """
    if websocket_client and websocket_client.is_connected:
        if websocket_client.client_id == websocket_client.active_controller_id:
            await websocket_client.send_audio_chunk(audio_bytes)
        # else:
            # logger.debug("Nicht aktiver Controller, überspringe das Senden von Audio-Input.")
            # Dies ist jetzt eher ein Debug-Fall, da der InputHandler gestoppt werden sollte
            # wenn wir nicht der aktive Controller sind.
    # else:
        # logger.debug("WebSocketClient nicht verbunden oder nicht verfügbar. Überspringe das Senden von Audio-Input.")


async def on_websocket_connect():
    """Wird aufgerufen, wenn der WebSocket erfolgreich verbunden ist."""
    logger.info("Successfully connected to the backend!")


async def on_websocket_error(e: Exception):
    """Wird aufgerufen, wenn ein WebSocket-Fehler auftritt."""
    logger.error(f"WebSocket error occurred: {e}", exc_info=True)


async def handle_tool_call(tool_name: str, args: Dict[str, Any], suggested_action: str):
    """Handler für Tool Calls vom Backend."""
    logger.info(f"⚙️ TOOL CALL: {tool_name}({json.dumps(args)}) - Suggested Action: {suggested_action}")
    await simulate_tool_call(tool_name, args, suggested_action)


async def handle_backend_message(data: Union[AllIncomingJsonEvents, bytes]):
    """Verarbeitet eingehende Nachrichten vom Backend."""
    global audio_input_handler, websocket_client

    if isinstance(data, bytes):
        logger.debug(f"Received {len(data)} bytes of audio data. Playing...")      
        # audio_output_handler.play_audio(data, incoming_samplerate=24000)
        audio_playback_queue.put_nowait(data)
    elif isinstance(data, dict):
        message_type = data.get("type")

        if message_type == "audio_interrupt":
            logger.warning("🚨 Received audio_interrupt. Stopping current audio playback!")
            
            # Lösche alle noch wartenden Audio-Chunks aus der Queue
            while not audio_playback_queue.empty():
                try:
                    audio_playback_queue.get_nowait()
                    audio_playback_queue.task_done()
                except asyncio.QueueEmpty:
                    break
                    
            # Beendet den aktuell laufenden Ton auf der Hardware
            # audio_output_handler.stop_playback()
            logger.info(f"System Message: {data.get('message', 'Audio interrupted by user speech.')}")

        elif message_type == "registration_ack":
            ack_data: RegistrationAckEvent = data
            logger.info(f"Registration acknowledged: {ack_data.get('message')}")
            # WebSocketClient aktualisiert seine internen IDs bereits. Hier nur zur Referenz.
            logger.info(f"My client ID: {websocket_client.client_id}, Active controller ID: {websocket_client.active_controller_id}")
            
            # Die Logik zum Starten/Stoppen der Aufnahme wird nun zentralisiert im
            # 'active_controller_change' Handler ausgeführt, der auch nach 'registration_ack'
            # (implizit durch die initiale Zuweisung) und explizit bei echten Änderungen feuert.
            # Ein manueller Start hier ist redundant und kann zu Race Conditions führen.
            # Stattdessen stellen wir sicher, dass der AudioInputHandler im 'active_controller_change'
            # entsprechend der initialen Controller-Rolle gestartet oder gestoppt wird.
            logger.debug("Registration ACK received. Active controller logic deferred to active_controller_change handling.")


        elif message_type == "active_controller_change":
            change_data: ActiveControllerChangeEvent = data
            new_type = change_data.get('new_active_controller_type')
            new_id = change_data.get('new_active_controller_id')
            
            logger.info(f"Active controller changed to: {new_type} (ID: {new_id})")
            
            if websocket_client and audio_input_handler:
                # THE FIX: Check if we are the 'hardware' client OR if the ID matches
                if new_type == "hardware" or websocket_client.client_id == new_id:
                    logger.info("I am the active controller. Starting audio input.")
                    await audio_input_handler.start_recording()
                else:
                    logger.info("Another client is now the active controller. Keeping mic ON for barge-in.")
                    # await audio_input_handler.stop_recording()

        elif message_type == "ai_response":
            ai_response: AIResponseEvent = data
            logger.info(f"AI Response (Text): {ai_response.get('text')}")
        elif message_type == "transcript":
            transcript_data: TranscriptEvent = data
            logger.info(f"Transcript ({'Final' if transcript_data.get('is_final') else 'Interim'}): {transcript_data.get('text')}")
        elif message_type == "system_message":
            system_message_data: SystemMessageEvent = data
            logger.info(f"System Message: {system_message_data.get('message')}")
        elif message_type == "error":
            error_data: ErrorEvent = data
            logger.error(f"Backend Error: {error_data.get('message')}")
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

def get_user_input_blocking():
    """Kapselt den blockierenden input()-Aufruf für den Text-Chat."""
    return input("Enter message (or 'exit' to quit): ")

async def main():
    global websocket_client, audio_input_handler, hardware_handler

    logger.info("Starting Squishy Pi Client.")

    hardware_handler = HardwareHandler(on_sensor_update_callback=send_sensor_data_to_gemini)
    await hardware_handler.start()

    websocket_client = WebSocketClient(
        ws_url=BACKEND_WS_URL,
        client_type="hardware",
        capabilities=CLIENT_CAPABILITIES,
        on_message_callback=handle_backend_message,
        on_connect_callback=on_websocket_connect,
        on_error_callback=on_websocket_error
    )
    websocket_client.set_tool_call_handler(handle_tool_call)

    audio_input_handler = AudioInputHandler(
        on_audio_data_callback=send_recorded_audio_to_websocket,
        target_channels=1,
        device_name_keywords=["UM10", "USB Audio Device"],
        rates_to_test=[48000, 44100, 16000]
    )
    
    if not await audio_input_handler.initialize():
        logger.error("AudioInputHandler konnte nicht initialisiert werden. Überprüfe die Hardware!")
        audio_input_handler.terminate()
        return

    playback_task = asyncio.create_task(audio_playback_worker())

    await websocket_client.connect()
    await asyncio.sleep(2) 

    if websocket_client.is_connected:
        # Initialer Check und ggf. Request for control
        if not websocket_client.active_controller_id: # Falls active_controller_id noch nicht gesetzt
            logger.warning("Active controller ID not yet set after connection. Waiting for it or requesting control.")
            await websocket_client.request_set_active_controller()
            await asyncio.sleep(1) # Gib dem Backend Zeit zu antworten

        if websocket_client.client_id == websocket_client.active_controller_id:
            logger.info("I am the active controller (initial or after request). Initiating persona greeting.")
            await websocket_client.send_text_message("Sag einmal nur das Wort Apfelbaum")
            # AudioInputHandler wird hier NICHT explizit gestartet,
            # da dies durch das `active_controller_change` Event in `handle_backend_message`
            # (das auch bei initialer Zuweisung getriggert wird) oder bei einem Wechsel geschieht.
        else:
            logger.warning("I am not the active controller. I can only listen.")
            # Auch hier wird der AudioInputHandler durch `active_controller_change` gestoppt,
            # falls er unerwartet lief.

        # Schleife für Text-Input (läuft parallel zur Audioverarbeitung)
        while websocket_client.is_connected:
            user_input = await asyncio.to_thread(get_user_input_blocking)
            
            if user_input.lower() == 'exit':
                break
            if websocket_client.client_id == websocket_client.active_controller_id:
                await websocket_client.send_text_message(user_input)
            else:
                logger.warning("Cannot send text message, I am not the active controller.")
            
            await asyncio.sleep(0.1)

    else:
        logger.error("Failed to connect to WebSocket, exiting.")

    # Aufräumen beim Beenden
    if audio_input_handler:
        await audio_input_handler.stop_recording()
        audio_input_handler.terminate()
    
    audio_playback_queue.put_nowait(None)

    if websocket_client:
        await websocket_client.disconnect()
    audio_output_handler.stop_all_streams()
    await hardware_handler.stop()
    logger.info("Squishy Pi Client stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("An unexpected error occurred in main.")