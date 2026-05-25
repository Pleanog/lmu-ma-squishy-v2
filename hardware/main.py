import asyncio
import logging
import sys
from typing import Union, Dict, Any, Optional
from client.websocket_client import (
    WebSocketClient,
    AllIncomingJsonEvents, # Verwende den neuen Union-Typ
    RegistrationAckEvent,
    ActiveControllerChangeEvent, # Neuer Typ
    AIResponseEvent,
    ToolCallEvent,
    TranscriptEvent,
    SystemMessageEvent, # Hinzugefügt
    ErrorEvent # Hinzugefügt
)
from client.audio_handler import AudioHandler
from client.audio_input_handler import AudioInputHandler
from config import BACKEND_WS_URL, CLIENT_CAPABILITIES

logging.basicConfig(level=logging.INFO, stream=sys.stdout, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialisiere den Audio-Output-Handler (für Sprachausgabe vom Backend)
audio_output_handler = AudioHandler(hardware_samplerate=48000, channels=2, dtype='float32', volume_factor=1.0)

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
            await websocket_client.send_audio_chunk(audio_bytes) # Nutze die Methode des WebSocketClients
        else:
            logger.debug("Nicht aktiver Controller, überspringe das Senden von Audio-Input.")
    else:
        logger.debug("WebSocketClient nicht verbunden oder nicht verfügbar. Überspringe das Senden von Audio-Input.")


async def on_websocket_connect():
    """Wird aufgerufen, wenn der WebSocket erfolgreich verbunden ist."""
    logger.info("Successfully connected to the backend!")
    # Hier keine direkte Aktion zum Starten der Audio-Aufnahme, da dies von active_controller_change abhängt.


async def on_websocket_error(e: Exception):
    """Wird aufgerufen, wenn ein WebSocket-Fehler auftritt."""
    logger.error(f"WebSocket error occurred: {e}", exc_info=True)
    # Hier könnte man Logik zum Wiederverbinden implementieren


async def handle_tool_call(tool_name: str, args: Dict[str, Any], suggested_action: str):
    """Handler für Tool Calls vom Backend."""
    logger.info(f"TOOL CALL: {tool_name}({args}) - Suggested Action: {suggested_action}")
    await simulate_tool_call(tool_name, args, suggested_action)


async def handle_backend_message(data: Union[AllIncomingJsonEvents, bytes]):
    """Verarbeitet eingehende Nachrichten vom Backend."""
    global audio_input_handler, websocket_client

    if isinstance(data, bytes):
        logger.debug(f"Received {len(data)} bytes of audio data. Playing...")      
        audio_output_handler.play_audio(data, incoming_samplerate=24000)
    elif isinstance(data, dict):
        message_type = data.get("type")

        if message_type == "registration_ack":
            ack_data: RegistrationAckEvent = data
            logger.info(f"Registration acknowledged: {ack_data.get('message')}")
            logger.info(f"My client ID: {websocket_client.client_id}, Active controller ID: {websocket_client.active_controller_id}")
            # Prüfe direkt nach Registrierung, ob wir der aktive Controller sind und starte ggf. Audio-Input
            if websocket_client.client_id == websocket_client.active_controller_id and audio_input_handler:
                logger.info("I am the initial active controller. Starting audio input.")
                await audio_input_handler.start_recording()
            elif websocket_client.client_id != websocket_client.active_controller_id and audio_input_handler:
                logger.info("Not the initial active controller, audio input will remain off.")
                await audio_input_handler.stop_recording() # Sicherstellen, dass es aus ist

        elif message_type == "active_controller_change":
            change_data: ActiveControllerChangeEvent = data
            logger.info(f"Active controller changed to: {change_data.get('new_active_controller_type')} ({change_data.get('new_active_controller_id')})")
            
            # Logik zum Starten/Stoppen der Audioaufnahme basierend auf dem aktiven Controller
            if websocket_client and audio_input_handler:
                if websocket_client.client_id == websocket_client.active_controller_id:
                    logger.info("I am now the active controller. Starting audio input.")
                    await audio_input_handler.start_recording()
                else:
                    logger.info("Another client is now the active controller. Stopping audio input.")
                    await audio_input_handler.stop_recording()

        elif message_type == "ai_response":
            ai_response: AIResponseEvent = data
            logger.info(f"AI Response (Text): {ai_response.get('text')}")
        elif message_type == "transcript":
            transcript_data: TranscriptEvent = data
            logger.info(f"Transcript ({'Final' if transcript_data.get('is_final') else 'Interim'}): {transcript_data.get('text')}")
        elif message_type == "tool_call":
            # Der Tool Call wird jetzt vom websocket_client.py selbst an handle_tool_call weitergeleitet
            # Hier müsste keine separate Logik mehr stehen, da es bereits im Client behandelt wird.
            # logger.info(f"Tool call event received, handled by dedicated handler.")
            pass # Der Handler wurde vom WebSocketClient aufgerufen

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
        # Hier würde die tatsächliche Hardware-Logik für LEDs aufgerufen werden
    elif tool_name == "play_sound_effect":
        effect_name = args.get("effect_name", "beep")
        logger.info(f"  -> Simulating: Play sound effect '{effect_name}'.")
        print(f"  [Sound Effect: {effect_name}]")
        # Hier würde die tatsächliche Sound-Logik aufgerufen werden
    elif tool_name == "get_sensor_data":
        sensor_type = args.get("sensor_type", "temperature")
        logger.info(f"  -> Simulating: Get data from {sensor_type} sensor.")
        print(f"  [Sensor Reading: {sensor_type} = 25.0 C (simulated)]")
        # Hier würde die tatsächliche Sensor-Logik aufgerufen werden
    else:
        logger.warning(f"  -> Unknown tool call simulation for '{tool_name}'.")

def get_user_input_blocking():
    """Kapselt den blockierenden input()-Aufruf für den Text-Chat."""
    return input("Enter message (or 'exit' to quit): ")

async def main():
    global websocket_client, audio_input_handler

    logger.info("Starting Squishy Pi Client.")

    # 1. WebSocketClient initialisieren
    websocket_client = WebSocketClient(
        ws_url=BACKEND_WS_URL,
        client_type="hardware",
        capabilities=CLIENT_CAPABILITIES,
        on_message_callback=handle_backend_message,
        on_connect_callback=on_websocket_connect,
        on_error_callback=on_websocket_error
    )
    # Setze den Tool Call Handler des WebSocketClients
    websocket_client.set_tool_call_handler(handle_tool_call)

    # 2. AudioInputHandler initialisieren
    audio_input_handler = AudioInputHandler(
        on_audio_data_callback=send_recorded_audio_to_websocket,
        target_channels=1,
        device_name_keywords=["UM10", "USB Audio Device"],
        rates_to_test=[48000, 44100, 16000]
    )
    
    # Warte auf die Initialisierung des Audio-Input-Handlers
    if not await audio_input_handler.initialize():
        logger.error("AudioInputHandler konnte nicht initialisiert werden. Überprüfe die Hardware!")
        audio_input_handler.terminate()
        return

    # 3. Verbindung zum WebSocket aufbauen
    await websocket_client.connect()
    # Gib dem WebSocket Zeit für die Registrierung und den Empfang der initialen active_controller_id
    await asyncio.sleep(2) 

    if websocket_client.is_connected:
        if websocket_client.client_id and websocket_client.client_id == websocket_client.active_controller_id:
            logger.info("I am the active controller (initial state). Initiating persona greeting.")
            await websocket_client.send_text_message("Sag einmal nur das Wort Apfelbaum")
            # Audioaufnahme wird bereits durch handle_backend_message nach registration_ack gestartet
        else:
            logger.warning("I am not the active controller (initial state). Requesting control...")
            await websocket_client.request_set_active_controller()
            await asyncio.sleep(1) # Kurze Wartezeit, um die Antwort zu erhalten
            if websocket_client.client_id == websocket_client.active_controller_id:
                logger.info("Successfully became the active controller! Initiating persona greeting.")
                await websocket_client.send_text_message("Sag einmal nur das Wort Pferdestall")
                # Audioaufnahme wird bereits durch handle_backend_message nach active_controller_change gestartet
            else:
                logger.warning("Failed to become active controller. I can only listen, no audio input from me.")

        # Schleife zum Senden von Text vom Pi an Gemini (optional, wenn primär Audio)
        # Diese Schleife ist nur für den manuellen Text-Input, der Audio-Input läuft parallel
        while websocket_client.is_connected:
            user_input = await asyncio.to_thread(get_user_input_blocking)
            
            if user_input.lower() == 'exit':
                break
            if websocket_client.client_id == websocket_client.active_controller_id:
                await websocket_client.send_text_message(user_input)
            else:
                logger.warning("Cannot send text message, I am not the active controller.")
            
            await asyncio.sleep(0.1) # Wichtige Pause, damit der Event-Loop nicht blockiert

    else:
        logger.error("Failed to connect to WebSocket, exiting.")

    # Aufräumen beim Beenden
    if audio_input_handler:
        await audio_input_handler.stop_recording()
        audio_input_handler.terminate()
    if websocket_client:
        await websocket_client.disconnect()
    audio_output_handler.stop_playback()
    logger.info("Squishy Pi Client stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("An unexpected error occurred in main.")