# FILE: app/models/events.py

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from models.client_state import ClientType, ClientCapability

# --- Base Event Model ---
class BaseEvent(BaseModel):
    type: str = Field(..., description="The type of the event.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# --- Incoming Events (from Clients to Server) ---

class RegisterEvent(BaseEvent):
    type: str = "register"
    client_type: ClientType
    capabilities: List[ClientCapability] = Field(default_factory=list)
    username: Optional[str] = None
    participant_id: Optional[str] = None

class AudioChunkEvent(BaseEvent):
    type: str = "audio_chunk"
    data: bytes

    class Config:
        arbitrary_types_allowed = True # Allow bytes type

class TextMessageEvent(BaseEvent):
    type: str = "text_message"
    text: str

class SensorEvent(BaseEvent):
    type: str = "sensor_event"
    sensor_id: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    event: Optional[str] = None # e.g., "petted", "tilted"
    intensity: Optional[str] = None

class ToolResponseEvent(BaseEvent):
    type: str = "tool_response"
    tool_call_id: str
    tool_name: str
    result: Dict[str, Any]

class SetActiveControllerEvent(BaseEvent):
    type: str = "set_active_controller"
    client_id: str # The client_id of the client requesting to become active

class ImageChunkEvent(BaseEvent):
    type: str = "image_chunk"
    data: str # Base64 encoded image data

class RoutingConfigUpdateEvent(BaseEvent):
    type: str = "routing_config_update"
    hardware_mic_enabled: Optional[bool] = None
    hardware_speaker_enabled: Optional[bool] = None
    ui_text_mode_enabled: Optional[bool] = None

# Union of all possible incoming event types
IncomingEventType = Union[
    RegisterEvent,
    AudioChunkEvent,
    TextMessageEvent,
    SensorEvent,
    ToolResponseEvent,
    SetActiveControllerEvent,
    ImageChunkEvent,
    RoutingConfigUpdateEvent,
]

# --- Outgoing Events (from Server to Clients) ---

class RegistrationAckEvent(BaseEvent):
    type: str = "registration_ack"
    client_id: str
    message: str = "Successfully registered."
    active_controller_id: Optional[str] = None
    current_active_controller_type: Optional[ClientType] = None
    routing_config: Optional[Dict[str, bool]] = None

class ActiveControllerChangeEvent(BaseEvent):
    type: str = "active_controller_change"
    new_active_controller_id: str
    new_active_controller_type: ClientType
    old_active_controller_id: Optional[str] = None
    old_active_controller_type: Optional[ClientType] = None

class TranscriptEvent(BaseEvent):
    type: str = "transcript"
    text: str
    is_final: bool

class AudioOutputEvent(BaseEvent):
    type: str = "audio_output"
    data: bytes

    class Config:
        arbitrary_types_allowed = True

class AudioInterruptEvent(BaseEvent):
    type: str = "audio_interrupt"
    message: str = "AI audio interrupted."

class ToolCallEvent(BaseEvent):
    type: str = "tool_call"
    tool_call_id: str
    tool_name: str
    args: Dict[str, Any]
    # For clients to decide how to handle: execute, simulate, visualize
    suggested_action: Optional[str] = None # e.g., "execute", "simulate", "visualize"

class AIResponseEvent(BaseEvent):
    type: str = "ai_response"
    text: str

class ErrorEvent(BaseEvent):
    type: str = "error"
    message: str
    code: Optional[int] = None

class SystemMessageEvent(BaseEvent):
    type: str = "system_message"
    message: str

class SessionResetEvent(BaseEvent):
    type: str = "session_reset"
    message: str = "Gemini session reset."

class SystemCommandEvent(BaseEvent):
    type: str = "system_command"
    command: str
    target: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

# Union of all possible outgoing event types
OutgoingEventType = Union[
    RegistrationAckEvent,
    ActiveControllerChangeEvent,
    TranscriptEvent,
    AudioOutputEvent,
    AudioInterruptEvent,
    ToolCallEvent,
    AIResponseEvent,
    ErrorEvent,
    SystemMessageEvent,
    SessionResetEvent,
    SystemCommandEvent,
]

class IncomingEvent(str, Enum):
    REGISTER = "register"
    AUDIO_CHUNK = "audio_chunk"
    TEXT_MESSAGE = "text_message"
    SENSOR_EVENT = "sensor_event"
    TOOL_RESPONSE = "tool_response"
    SET_ACTIVE_CONTROLLER = "set_active_controller"
    IMAGE_CHUNK = "image_chunk"
    ROUTING_CONFIG_UPDATE = "routing_config_update"

    @property
    def model(self):
        return {
            IncomingEvent.REGISTER: RegisterEvent,
            IncomingEvent.AUDIO_CHUNK: AudioChunkEvent,
            IncomingEvent.TEXT_MESSAGE: TextMessageEvent,
            IncomingEvent.SENSOR_EVENT: SensorEvent,
            IncomingEvent.TOOL_RESPONSE: ToolResponseEvent,
            IncomingEvent.SET_ACTIVE_CONTROLLER: SetActiveControllerEvent,
            IncomingEvent.IMAGE_CHUNK: ImageChunkEvent,
            IncomingEvent.ROUTING_CONFIG_UPDATE: RoutingConfigUpdateEvent,
        }[self]

class OutgoingEvent(str, Enum):
    REGISTRATION_ACK = "registration_ack"
    ACTIVE_CONTROLLER_CHANGE = "active_controller_change"
    TRANSCRIPT = "transcript"
    AUDIO_OUTPUT = "audio_output"
    AUDIO_INTERRUPT = "audio_interrupt"
    TOOL_CALL = "tool_call"
    AI_RESPONSE = "ai_response"
    ERROR = "error"
    SYSTEM_MESSAGE = "system_message"
    SESSION_RESET = "session_reset"
    SYSTEM_COMMAND = "system_command"

    @property
    def model(self):
        return {
            OutgoingEvent.REGISTRATION_ACK: RegistrationAckEvent,
            OutgoingEvent.ACTIVE_CONTROLLER_CHANGE: ActiveControllerChangeEvent,
            OutgoingEvent.TRANSCRIPT: TranscriptEvent,
            OutgoingEvent.AUDIO_OUTPUT: AudioOutputEvent,
            OutgoingEvent.AUDIO_INTERRUPT: AudioInterruptEvent,
            OutgoingEvent.TOOL_CALL: ToolCallEvent,
            OutgoingEvent.AI_RESPONSE: AIResponseEvent,
            OutgoingEvent.ERROR: ErrorEvent,
            OutgoingEvent.SYSTEM_MESSAGE: SystemMessageEvent,
            OutgoingEvent.SESSION_RESET: SessionResetEvent,
            OutgoingEvent.SYSTEM_COMMAND: SystemCommandEvent,
        }[self]