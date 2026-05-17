# FILE: app/clients/frontend.py

# This file is illustrative. In the new architecture, the specific logic for
# a 'frontend' client is not housed in a dedicated Python file on the backend.
# Instead, the `WebSocketClient` and `WebSocketManager` handle the generic
# WebSocket connection, and the `MessageRouter` directs events based on
# the `client_type` and `capabilities` declared by the *frontend client itself*
# during registration.

# The 'frontend' is defined by its `client_type` and the `capabilities` it sends
# in its initial `RegisterEvent`.

# Example of how a frontend client might register:
"""
# From frontend JavaScript:
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
    console.log("WebSocket connected.");
    ws.send(JSON.stringify({
        "type": "register",
        "client_type": "frontend",
        "capabilities": [
            "audio_input",
            "audio_output",
            "text_input",
            "text_output",
            "tool_visualization",
            "sensor_simulation",
            "transcription_view",
            "ai_response_view"
        ]
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received from backend:", data);

    if (data.type === "registration_ack") {
        console.log("Frontend registered with client ID:", data.client_id);
    } else if (data.type === "active_controller_change") {
        console.log("Active controller changed to:", data.new_active_controller_type, data.new_active_controller_id);
    } else if (data.type === "transcript") {
        console.log("Transcript:", data.text, data.is_final ? "(Final)" : "");
    } else if (data.type === "audio_output") {
        // Handle audio playback
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioContext.decodeAudioData(event.data) // Assuming backend sends raw audio bytes
            .then(buffer => {
                const source = audioContext.createBufferSource();
                source.buffer = buffer;
                source.connect(audioContext.destination);
                source.start(0);
            });
    } else if (data.type === "tool_call") {
        console.log("Tool Call received:", data.tool_name, data.args, "Suggested action:", data.suggested_action);
        // Frontend logic to visualize or simulate the tool call
        if (data.suggested_action === "visualize" || data.suggested_action === "simulate") {
            // Update UI to show LED change or vibration etc.
            console.log(`Frontend visualizing/simulating ${data.tool_name} with args:`, data.args);
            // Example: If it's an LED call, update a UI element
            if (data.tool_name === "set_led_color") {
                document.getElementById('squishy-led-visual').style.backgroundColor = data.args.color;
            }
            // If frontend is in simulation mode and meant to respond, send a tool_response
            // This is hypothetical and depends on your frontend's simulation fidelity
            if (data.suggested_action === "simulate") {
                ws.send(JSON.stringify({
                    "type": "tool_response",
                    "tool_call_id": data.tool_call_id,
                    "tool_name": data.tool_name,
                    "result": {"status": "simulated", "message": `Frontend simulated ${data.tool_name}`}
                }));
            }
        }
    }
    // ... handle other event types
};

// Example of sending simulated sensor event from frontend
function sendSimulatedPettingEvent() {
    ws.send(JSON.stringify({
        "type": "sensor_event",
        "sensor_id": "simulated_touch_sensor",
        "event": "petted",
        "value": 1,
        "intensity": "gentle"
    }));
}
"""

# The backend's `app/clients` directory will *not* contain Python files
# for frontend or hardware "client definitions" in the same way `main.py`
# used to have separate `websocket_endpoint` functions.
# Instead, `app/clients/capabilities.py` defines the *expected* capabilities
# for different client types, which the frontend/hardware client itself uses
# to inform the backend during registration.