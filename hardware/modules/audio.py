import time
import logging
import os
import requests
import tempfile

# Try importing playsound, mock if not installed
try:
    from playsound import playsound
    HAS_AUDIO_OUT = True
except ImportError:
    HAS_AUDIO_OUT = False

class AudioManager:
    def __init__(self):
        pass

    def record_audio(self, duration=2):
        """
        SIMULATION: Instead of recording mic, returns a pre-existing file.
        In production, this would use PyAudio/ReSpeaker drivers.
        """
        logging.info("audio     | 🔴 Recording (Simulated)...")
        time.sleep(1) # Simulate the time taken to speak
        
        # Ensure you have a 'test_input.wav' in the hardware folder!
        if os.path.exists("test_input.mp3"):
            return "test_input.mp3"
        else:
            logging.warning("audio     | ⚠️ No test_input.mp3 found! Please create one.")
            return None

    def play_audio(self, url):
        """Downloads and plays the AI response"""
        logging.info(f"audio     | 🟢 Playing Stream: {url}")
        
        # 1. Download to temp file
        try:
            r = requests.get(url)
            if r.status_code == 200:
                # Save temp
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp.write(r.content)
                temp.close()
                
                # 2. Play
                if HAS_AUDIO_OUT:
                    # playsound(temp.name) # Uncomment if you install playsound
                    logging.info("audio     | 🔊 [SOUND PLAYING...]")
                    time.sleep(2) # Simulate playback time
                else:
                    logging.info("audio     | 🔊 [SOUND PLAYING (Mock)...]")
                
                # Cleanup
                os.remove(temp.name)
        except Exception as e:
            logging.error(f"audio     | ❌ Playback failed: {e}")