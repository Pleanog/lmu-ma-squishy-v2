# squishy_pi_client/main.py

import asyncio
import logging
import sys
from typing import Union
from client.websocket_client import WebSocketClient, IncomingBackendJsonEvent, RegistrationAckEvent, AIResponseEvent
from config import BACKEND_WS_URL, CLIENT_CAPABILITIES

# Konfiguriere Logging für eine bessere Ausgabe
logging.basicConfig(level=logging.INFO, stream=sys.stdout, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Callbacks für den WebSocketClient ---

def on_connect():
    """Wird aufgerufen, wenn die WebSocket-Verbindung erfolgreich ist."""
    logger.info("Successfully connected to the backend!")

def on_error(e: Exception):
    """Wird bei einem Fehler in der WebSocket-Verbindung aufgerufen."""
    logger.error(f"WebSocket error occurred: {e}")

async def handle_backend_message(data: Union[IncomingBackendJsonEvent, bytes]):
    """
    Verarbeitet Nachrichten, die vom Backend empfangen werden.
    Für den initialen Text-Chat konzentrieren wir uns auf Textausgaben.
    """
    if isinstance(data, bytes):
        logger.debug(f"Received {len(data)} bytes of audio data. (Ignoring for text-only mode)")
        # Hier würde später audio_handler.play_audio(data) aufgerufen
    elif isinstance(data, dict): # Geparsstes JSON-Objekt
        message_type = data.get("type")
        if message_type == "registration_ack":
            ack_data: RegistrationAckEvent = data
            logger.info(f"Registration acknowledged: {ack_data.get('message')}")
        elif message_type == "ai_response":
            ai_response: AIResponseEvent = data
            logger.info(f"AI Response: {ai_response.get('text')}")
        elif message_type == "system_message":
            logger.info(f"System Message: {data.get('message')}")
        elif message_type == "error":
            logger.error(f"Backend Error: {data.get('message')}")
        else:
            logger.info(f"Received unknown JSON message: {data}")
    else:
        logger.warning(f"Received unexpected message format: {type(data)} - {data}")


async def main():
    logger.info("Starting Squishy Pi Client - Text-only mode.")

    websocket_client = WebSocketClient(
        ws_url=BACKEND_WS_URL,
        client_type="hardware",
        capabilities=CLIENT_CAPABILITIES,
        on_message_callback=handle_backend_message,
        on_connect_callback=on_connect,
        on_error_callback=on_error
    )

    # Starte die WebSocket-Verbindung
    await websocket_client.connect()

    # Gib dem Client etwas Zeit für die Registrierung und den ersten Kontakt
    await asyncio.sleep(2) 

    if websocket_client.is_connected:
        # Frage, ob der Pi den aktiven Controller übernehmen soll
        # Dies ist wichtig, da nur der aktive Controller den initialen Persona-Prompt senden kann
        # und dann Text/Audio-Input senden darf.
        logger.info(f"Current active controller ID: {websocket_client.active_controller_id}")
        logger.info(f"My client ID: {websocket_client.client_id}")

        if websocket_client.client_id and websocket_client.client_id == websocket_client.active_controller_id:
            logger.info("I am the active controller.")
            # Hier kann der Pi den initialen Persona-Gruß triggern
            await websocket_client.send_initiate_persona_greeting()
        else:
            logger.warning("I am not the active controller. Requesting control...")
            await websocket_client.request_set_active_controller()
            await asyncio.sleep(1) # Kurze Pause, um auf die Bestätigung zu warten
            if websocket_client.client_id == websocket_client.active_controller_id:
                logger.info("Successfully became the active controller!")
                await websocket_client.send_initiate_persona_greeting()
            else:
                logger.warning("Failed to become active controller. I can only listen.")


        # Einfache Schleife zum Senden von Text vom Pi an Gemini
        while websocket_client.is_connected:
            user_input = input("Enter message (or 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            if websocket_client.client_id == websocket_client.active_controller_id:
                await websocket_client.send_text_message(user_input)
            else:
                logger.warning("Cannot send message, I am not the active controller.")
    else:
        logger.error("Failed to connect to WebSocket, exiting.")

    await websocket_client.disconnect()
    logger.info("Squishy Pi Client stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception("An unexpected error occurred in main.")