# FILE: app/clients/capabilities.py

from models.client_state import ClientType, ClientCapability

# Define standard capabilities for different client types

FRONTEND_CLIENT_CAPABILITIES = {
    ClientCapability.AUDIO_INPUT,
    ClientCapability.AUDIO_OUTPUT,
    ClientCapability.TEXT_INPUT,
    ClientCapability.TEXT_OUTPUT,
    ClientCapability.TOOL_VISUALIZATION,
    ClientCapability.SENSOR_SIMULATION,
    ClientCapability.TRANSCRIPTION_VIEW,
    ClientCapability.AI_RESPONSE_VIEW,
    # Add other frontend-specific capabilities as needed
}

HARDWARE_CLIENT_CAPABILITIES = {
    # ClientCapability.AUDIO_INPUT,
    # ClientCapability.AUDIO_OUTPUT,
    # ClientCapability.TEXT_INPUT,
    # ClientCapability.TEXT_OUTPUT, # For receiving AI text responses
    ClientCapability.TOOL_EXECUTION,
    ClientCapability.SENSOR_INPUT,
    # ClientCapability.LED_CONTROL,
    # ClientCapability.VIBRATION_CONTROL,
    # ClientCapability.SOUND_PLAYBACK,
    # Add other hardware-specific capabilities as needed
}

MONITOR_CLIENT_CAPABILITIES = {
    ClientCapability.TEXT_OUTPUT,
    ClientCapability.TOOL_VISUALIZATION,
    ClientCapability.TRANSCRIPTION_VIEW,
    ClientCapability.AI_RESPONSE_VIEW,
    # Monitor clients are typically passive observers
}

def get_default_capabilities(client_type: ClientType) -> set[ClientCapability]:
    """Returns the default set of capabilities for a given client type."""
    if client_type == ClientType.FRONTEND:
        return FRONTEND_CLIENT_CAPABILITIES
    elif client_type == ClientType.HARDWARE:
        return HARDWARE_CLIENT_CAPABILITIES
    elif client_type == ClientType.MONITOR:
        return MONITOR_CLIENT_CAPABILITIES
    return set()