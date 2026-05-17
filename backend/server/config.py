# FILE: app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL: str = os.getenv("MODEL", "gemini-3.1-flash-live-preview")
    PB_URL: str = os.getenv("PB_URL", "")
    PB_ADMIN_EMAIL: str = os.getenv("PB_ADMIN_EMAIL", "")
    PB_ADMIN_PASS: str = os.getenv("PB_ADMIN_PASS", "")

    AUDIO_SAMPLE_RATE: int = 16000 # Assuming clients provide 16kHz audio

settings = Settings()