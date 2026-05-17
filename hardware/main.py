import asyncio
from client.websocket_client import WebSocketClient
from client.audio_handler import AudioHandler
from client.hardware_manager import HardwareManager
from config import BACKEND_WS_URL, CLIENT_CAPABILITIES

async def main():
    print("Starting Squishy Pi Client...")

    # Initialisiere HardwareManager
    hardware_manager = HardwareManager()
    # Initialisiere AudioHandler
    audio_handler = AudioHandler()

    # Initialisiere WebSocketClient
    # on_message_from_backend wird von websocket_client gerufen, wenn Daten vom Backend kommen
    # on_audio_data_for_backend wird von audio_handler gerufen, wenn Mic-Daten bereit sind
    # on_sensor_event_for_backend wird von hardware_manager gerufen, wenn Sensor-Event auftritt
    websocket_client = WebSocketClient(
        ws_url=BACKEND_WS_URL,
        client_type="hardware",
        capabilities=CLIENT_CAPABILITIES,
        on_message_from_backend=audio_handler.handle_backend_message, # Audio/Text vom Backend
        on_audio_data_for_backend=audio_handler.send_audio_to_websocket, # Callbacks müssen sich noch registrieren
        on_sensor_event_for_backend=hardware_manager.send_sensor_event_to_websocket # Callbacks müssen sich noch registrieren
    )
    
    # AudioHandler und HardwareManager müssen wissen, wie sie Daten senden
    audio_handler.set_websocket_sender(websocket_client.send_audio_chunk)
    hardware_manager.set_websocket_sender(websocket_client.send_sensor_event)
    
    # WebSocketClient muss wissen, wohin er Tool-Calls schickt
    websocket_client.set_tool_call_handler(hardware_manager.handle_tool_call)

    # Verbinde zum Backend
    await websocket_client.connect()

    # Starte Audio-Aufnahme
    await audio_handler.start_audio_input()
    
    # Starte Sensor-Überwachung
    hardware_manager.start_monitoring()

    # Bleibe am Laufen, bis manuell beendet (z.B. Strg+C)
    while True:
        await asyncio.sleep(1) # Halte den Event-Loop am Leben

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Client stopped by user.")
    finally:
        # Hier cleanup-Routinen aufrufen
        pass