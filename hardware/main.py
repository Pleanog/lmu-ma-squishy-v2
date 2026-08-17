import asyncio
import logging
import os
import sys
from typing import Any, Optional, Union

from client.hardware_handler import HardwareHandler
from client.websocket_client import (
    AIResponseEvent,
    AllIncomingJsonEvents,
    ErrorEvent,
    RegistrationAckEvent,
    SystemMessageEvent,
    ToolCallEvent,
    TranscriptEvent,
    WebSocketClient,
)
from config import BACKEND_WS_URL, CLIENT_CAPABILITIES

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

websocket_client: Optional[WebSocketClient] = None
hardware_handler: Optional[HardwareHandler] = None


async def send_sensor_data_to_server(
    sensor_id: str,
    event_type: str,
    value: Any,
    intensity: Optional[str] = None,
):
    if websocket_client and websocket_client.is_connected:
        logger.info(
            "Sende Sensor-Event: sensor_id=%s, event=%s, value=%s, intensity=%s",
            sensor_id,
            event_type,
            value,
            intensity,
        )
        await websocket_client.send_sensor_event(sensor_id, event_type, value, intensity)


async def on_websocket_connect():
    logger.info("Successfully connected to the backend.")


async def on_websocket_error(e: Exception):
    logger.error("WebSocket error occurred: %s", e, exc_info=True)


async def handle_backend_message(data: Union[AllIncomingJsonEvents, bytes]):
    if isinstance(data, bytes):
        logger.debug("Ignoring %s bytes (hardware audio playback disabled).", len(data))
        return

    if not isinstance(data, dict):
        logger.warning("Received unexpected message format: %s - %s", type(data), data)
        return

    message_type = data.get("type")

    if message_type == "registration_ack":
        ack_data: RegistrationAckEvent = data
        logger.info("Registration acknowledged: %s", ack_data.get("message"))
    elif message_type == "ai_response":
        ai_response: AIResponseEvent = data
        logger.info("AI Response (Text): %s", ai_response.get("text"))
    elif message_type == "transcript":
        transcript_data: TranscriptEvent = data
        logger.info(
            "Transcript (%s): %s",
            "Final" if transcript_data.get("is_final") else "Interim",
            transcript_data.get("text"),
        )
    elif message_type == "system_message":
        system_message_data: SystemMessageEvent = data
        logger.info("System Message: %s", system_message_data.get("message"))
    elif message_type == "error":
        error_data: ErrorEvent = data
        logger.error("Backend Error: %s", error_data.get("message"))
    elif message_type == "tool_call":
        tool_call_data: ToolCallEvent = data
        logger.info(
            "Tool Call Received: %s with args: %s and suggested_action: %s",
            tool_call_data.get("tool_name"),
            tool_call_data.get("args"),
            tool_call_data.get("suggested_action"),
        )
    elif message_type == "system_command":
        command = data.get("command") or data.get("action")
        logger.warning("System command received: %s", command)
        if command == "restart":
            logger.warning("Restart command received. Restarting squishy service...")
            if websocket_client:
                await websocket_client.disconnect()
            os.system("sudo systemctl restart squishy")
    else:
        logger.warning("Received unknown JSON message: %s", data)


async def main():
    global websocket_client, hardware_handler

    logger.info("Starting Squishy hardware client (sensors + tool execution only).")

    hardware_handler = HardwareHandler(on_sensor_update_callback=send_sensor_data_to_server)

    websocket_client = WebSocketClient(
        ws_url=BACKEND_WS_URL,
        client_type="hardware",
        capabilities=CLIENT_CAPABILITIES,
        on_message_callback=handle_backend_message,
        on_connect_callback=on_websocket_connect,
        on_error_callback=on_websocket_error,
    )
    websocket_client.set_tool_call_handler(hardware_handler.handle_tool_call)

    await websocket_client.connect()
    await hardware_handler.start()

    if not websocket_client.is_connected:
        logger.error("Failed to connect to WebSocket, exiting.")
    else:
        while websocket_client.is_connected:
            await asyncio.sleep(0.5)

    if websocket_client:
        await websocket_client.disconnect()
    if hardware_handler:
        await hardware_handler.stop()

    logger.info("Squishy hardware client stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user (KeyboardInterrupt).")
    except Exception:
        logger.exception("An unexpected error occurred in main.")
