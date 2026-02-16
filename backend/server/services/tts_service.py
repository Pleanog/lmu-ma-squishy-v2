import tempfile
import logging
from gtts import gTTS

class TTSService:
    def text_to_speech(self, text):
        try:
            tts = gTTS(text=text, lang='en', slow=False) 
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp.close()
            tts.save(temp.name)
            return temp.name
        except Exception as e:
            logging.error(f"TTS Error: {e}")
            return None