# config.py

# BACKEND_WS_URL = "ws://127.0.0.1:8000/ws" # IP deines Backend-Servers anpassen!
# BACKEND_WS_URL = "ws://100.68.58.11:8000/ws" # Tailscale von Philipp laptop
BACKEND_WS_URL = "ws://100.107.127.25:8000/ws" # Tailscale von Aphrodite VR Laptop
# BACKEND_WS_URL = "ws://192.168.1.103:8000/ws" # Local Laptop
# BACKEND_WS_URL = "ws://192.168.1.xxx:8000/ws" # TODO: IP des Backend-Servers anpassen!

AUDIO_SAMPLE_RATE_INPUT = 16000 # für Mikrofon-Input zu Gemini
AUDIO_SAMPLE_RATE_OUTPUT = 24000 # von Gemini erhalten
AUDIO_CHUNK_SIZE = 1024 # Buffer-Größe für PyAudio
AUDIO_FORMAT_INPUT = 8 # pyaudio.paInt16 (16-bit signed PCM)
AUDIO_FORMAT_OUTPUT = 8 # pyaudio.paInt16

# Echo-/Barge-In-Verhalten:
# True = robustes Half-Duplex-Fallback: Während KI-Audio lokal abgespielt wird,
#        wird Mikrofon-Input Richtung Backend stummgeschaltet.
# False = Mikrofon bleibt aktiv; setzt voraus, dass ReSpeaker/AEC sauber arbeitet.
DISABLE_MIC_WHILE_AI_SPEAKS = True

# Kleiner Nachlauf nach der Wiedergabe, damit Resthall vom Lautsprecher nicht
# sofort wieder als User-Interrupt erkannt wird.
MIC_REENABLE_DELAY_MS = 350

# Optionaler Noise Gate Schwellenwert für den Mikrofon-Upload.
NOISE_GATE_THRESHOLD = 300

# Fähigkeiten des Hardware-Clients, passend zu deinem Backend
CLIENT_CAPABILITIES = [
    "audio_input",
    "audio_output",
    "sensor_input",
    "tool_execution",
    "text_input",
    "text_output"
]

# GPIO Pin Konfiguration (Beispiele)
LED_PIN = 17 # GPIO17 für eine LED
BUTTON_PIN = 27 # GPIO27 für einen Taster
# ... weitere Pins für Touch-Sensoren, IMU (I2C Adressen)