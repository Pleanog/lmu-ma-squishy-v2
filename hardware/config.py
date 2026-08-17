# config.py

# BACKEND_WS_URL = "ws://127.0.0.1:8000/ws" # IP deines Backend-Servers anpassen!
# BACKEND_WS_URL = "ws://100.68.58.11:8000/ws" # Tailscale von Philipp laptop
BACKEND_WS_URL = "ws://100.107.127.25:8000/ws" # Tailscale von Aphrodite VR Laptop
# BACKEND_WS_URL = "ws://192.168.1.103:8000/ws" # Local Laptop
# BACKEND_WS_URL = "ws://192.168.1.xxx:8000/ws" # TODO: IP des Backend-Servers anpassen!

# Fähigkeiten des Hardware-Clients, passend zu deinem Backend
CLIENT_CAPABILITIES = [
    "sensor_input",
    "tool_execution",
]

# GPIO Pin Konfiguration (Beispiele)
LED_PIN = 17 # GPIO17 für eine LED
BUTTON_PIN = 27 # GPIO27 für einen Taster
# ... weitere Pins für Touch-Sensoren, IMU (I2C Adressen)
