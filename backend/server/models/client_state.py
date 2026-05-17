# FILE: app/models/client_state.py

from enum import Enum
from typing import Set
from pydantic import BaseModel

class ClientType(str, Enum):
    FRONTEND = "frontend"
    HARDWARE = "hardware"
    MONITOR = "monitor" # For future-proofing

class ClientCapability(str, Enum):
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"
    TEXT_INPUT = "text_input"
    TEXT_OUTPUT = "text_output"
    TOOL_EXECUTION = "tool_execution" # For hardware to execute tools
    TOOL_SIMULATION = "tool_simulation" # For frontend to simulate tool effects
    TOOL_VISUALIZATION = "tool_visualization" # For frontend to display tool calls
    SENSOR_INPUT = "sensor_input" # For hardware to send real sensor data
    SENSOR_SIMULATION = "sensor_simulation" # For frontend to send fake sensor data
    LED_CONTROL = "led_control"
    VIBRATION_CONTROL = "vibration_control"
    SOUND_PLAYBACK = "sound_playback"
    TRANSCRIPTION_VIEW = "transcription_view"
    AI_RESPONSE_VIEW = "ai_response_view"

class WebSocketClientState(BaseModel):
    client_id: str
    client_type: ClientType
    capabilities: Set[ClientCapability]

    class Config:
        use_enum_values = True
        frozen = True # State should be immutable after creation