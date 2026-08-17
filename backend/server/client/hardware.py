# FILE: app/clients/hardware.py

# Similar to `app/clients/frontend.py`, this file is illustrative.
# The backend's `app/clients` directory will *not* contain Python files
# for hardware "client definitions" in the same way `main.py`
# used to have separate `websocket_endpoint` functions.
# Instead, the hardware client (e.g., a Raspberry Pi script) will connect
# to the *single* `/ws` endpoint and register itself with its type and capabilities.

# The 'hardware' is defined by its `client_type` and the `capabilities` it sends
# in its initial `RegisterEvent`.

# Example of how a hardware client (e.g., Python on Raspberry Pi) might register:
"""
# hardware_client.py (on Raspberry Pi)

import asyncio
import websockets
import json
import base64
import logging

# Assume you have functions to control hardware (LED, vibration, sound)
async def set_led(color: str):
    logging.info(f"HARDWARE: Setting LED color to {color}")
    # Actual hardware control code here (e.g., GPIO commands)
    return {"status": "success", "message": f"LED set to {color}"}

async def play_sound(sound_type: str):
    logging.info(f"HARDWARE: Playing sound '{sound_type}'")
    # Actual sound playback code here
    return {"status": "success", "message": f"Playing {sound_type} sound"}

async def vibrate(pattern: str):
    logging.info(f"HARDWARE: Vibrating with pattern '{pattern}'")
    # Actual vibration control code here
    return {"status": "success", "message": f"Vibrating with {pattern} pattern"}

# Example tool mapping for hardware
HARDWARE_TOOL_EXECUTION_MAP = {
    "set_led_color": set_led,
    "play_squishy_sound": play_sound,
    "vibrate_squishy": vibrate,
}

logging.basicConfig(level=logging.INFO)

async def connect_to_backend():
    uri = "ws://localhost:8000/ws" # Or your server's IP
    async with websockets.connect(uri) as websocket:
        logging.info("Hardware client connected to backend.")

        # Register as hardware client
        await websocket.send(json.dumps({
            "type": "register",
            "client_type": "hardware",
            "capabilities": [
                "tool_execution",
                "sensor_input",
                "led_control",
                "vibration_control",
            ]
        }))

        async def send_sensor_events():
            # Simulate sending sensor data
            while True:
                # In a real scenario, read from physical sensors
                sensor_data = {
                    "type": "sensor_event",
                    "sensor_id": "touch_sensor_1",
                    "event": "petted",
                    "value": 1,
                    "intensity": "gentle"
                }
                await websocket.send(json.dumps(sensor_data))
                await asyncio.sleep(5) # Send every 5 seconds

        async def receive_messages():
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logging.debug(f"Received JSON: {data}")

                    if data.get("type") == "registration_ack":
                        logging.info(f"Hardware registered with client ID: {data.client_id}")
                    elif data.get("type") == "tool_call":
                        tool_name = data["tool_name"]
                        args = data["args"]
                        tool_call_id = data["tool_call_id"]
                        logging.info(f"Received tool call: {tool_name} with args: {args}")

                        if data.get("suggested_action") == "execute":
                            if tool_name in HARDWARE_TOOL_EXECUTION_MAP:
                                func = HARDWARE_TOOL_EXECUTION_MAP[tool_name]
                                result = await func(**args)
                                # Send response back to backend
                                await websocket.send(json.dumps({
                                    "type": "tool_response",
                                    "tool_call_id": tool_call_id,
                                    "tool_name": tool_name,
                                    "result": result
                                }))
                            else:
                                logging.warning(f"No handler for tool '{tool_name}' on hardware.")
                                await websocket.send(json.dumps({
                                    "type": "tool_response",
                                    "tool_call_id": tool_call_id,
                                    "tool_name": tool_name,
                                    "result": {"status": "error", "message": f"Tool '{tool_name}' not supported by hardware."}
                                }))
                        else:
                            logging.info(f"Hardware client received tool call '{tool_name}' but not suggested for execution.")
                except json.JSONDecodeError:
                    logging.warning(f"Received non-JSON message: {message}")

        await asyncio.gather(
            send_sensor_events(),
            receive_messages()
        )

if __name__ == "__main__":
    asyncio.run(connect_to_backend())
"""

# The backend's `app/clients` directory is meant to hold capabilities definitions,
# not client-specific Python code that runs on the backend.