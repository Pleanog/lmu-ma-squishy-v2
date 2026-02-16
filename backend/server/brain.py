import os
import time
import logging
import threading
import requests
import tempfile
import mimetypes
from dotenv import load_dotenv
from pocketbase import PocketBase
from google import genai
from google.genai import types
from gtts import gTTS

# Load environment variables
load_dotenv()

# Configuration
PB_URL = os.getenv("PB_URL")
ADMIN_EMAIL = os.getenv("PB_ADMIN_EMAIL")
ADMIN_PASS = os.getenv("PB_ADMIN_PASS")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class AIBrain:
    def __init__(self):
        self.pb = PocketBase(PB_URL)
        # 1. Connect to PocketBase
        self.auth_admin()
        # 2. Connect to Google AI
        self.setup_gemini()

    def auth_admin(self):
        logging.info(f"🔌 Connecting to PocketBase at {PB_URL}...")
        try:
            self.pb.admins.auth_with_password(ADMIN_EMAIL, ADMIN_PASS)
            logging.info("✅ PocketBase Admin Connected!")
        except Exception as e:
            logging.error(f"❌ Failed to authenticate: {e}")
            exit(1)

    def setup_gemini(self):
        try:
            self.client = genai.Client(api_key=GEMINI_KEY)
            logging.info("✨ Gemini Client Initialized")
        except Exception as e:
            logging.error(f"❌ Failed to init Gemini: {e}")

    def download_file(self, collection_id, record_id, filename):
        """Downloads audio from PB using the Admin Token"""
        url = f"{PB_URL}/api/files/{collection_id}/{record_id}/{filename}"
        headers = { "Authorization": self.pb.auth_store.token }
        
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                ext = os.path.splitext(filename)[1]
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp.write(r.content)
                temp.close()
                return temp.name
            else:
                logging.error(f"Download blocked (Status {r.status_code}).")
        except Exception as e:
            logging.error(f"Download failed: {e}")
        return None

    def generate_speech_free(self, text):
        try:
            tts = gTTS(text=text, lang='en', slow=False) 
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp.close()
            tts.save(temp.name)
            return temp.name
        except Exception as e:
            logging.error(f"TTS Error: {e}")
            return None

    def build_system_prompt(self, metadata):
        prompt = (
            "You are a helpful, sentient hardware companion. "
            "CRITICAL INSTRUCTION: Keep your answer extremely short. "
            "Maximum 2 sentences. No bullet points. Be conversational."
        )
        if metadata.get('brightness') == 'low': prompt += " It is dark. Whisper."
        if metadata.get('shaken'): prompt += " URGENT: I was shaken! Be chaotic!"
        return prompt

    def process_task(self, record):
        """The worker function that runs in a thread"""
        audio_input_path = None
        audio_output_path = None
        
        try:
            logging.info(f"📩 Processing message from {record.id}")

            # 1. Download Audio
            user_audio_data = None
            mime_type = "audio/wav"

            if record.audio:
                logging.info(f"🎤 Audio detected: {record.audio}")
                audio_input_path = self.download_file(record.collection_id, record.id, record.audio)
                
                if audio_input_path:
                    guessed_mime = mimetypes.guess_type(audio_input_path)[0]
                    if guessed_mime: mime_type = guessed_mime
                    
                    with open(audio_input_path, "rb") as f:
                        user_audio_data = f.read()

            # 2. Prepare Gemini Content
            metadata = record.metadata if record.metadata else {}
            sys_prompt = self.build_system_prompt(metadata)
            
            contents = []
            if record.content: contents.append(record.content)
            
            if user_audio_data:
                contents.append(types.Part.from_bytes(data=user_audio_data, mime_type=mime_type))

            if not contents:
                logging.warning("⚠️ Empty message. Skipping.")
                return

            # 3. Call Gemini
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt,
                    max_output_tokens=60
                )
            )
            ai_reply = response.text
            logging.info(f"🤖 AI Reply: {ai_reply}")

            # 4. Generate & Upload Reply
            audio_output_path = self.generate_speech_free(ai_reply)
            
            files_payload = {}
            if audio_output_path:
                files_payload['audio'] = ('reply.mp3', open(audio_output_path, 'rb'))

            self.pb.collection('messages').create({
                "conversation": record.conversation,
                "content": ai_reply,
                "sender": "ai",
                "metadata": { "generated_by": "gemini-3-flash-preview" }
            }, files=files_payload)
            
            logging.info("✅ Reply sent!")

        except Exception as err:
            logging.error(f"Error in task: {err}")
        
        finally:
            # Cleanup
            if audio_input_path and os.path.exists(audio_input_path):
                os.remove(audio_input_path)
            if audio_output_path:
                try: files_payload.get('audio')[1].close()
                except: pass
                if os.path.exists(audio_output_path): os.remove(audio_output_path)

    def start(self):
        logging.info("👂 Listening for messages...")
        
        # RESTORED: The "Lambda + Thread" pattern that worked for you
        self.pb.collection('messages').subscribe(lambda e: 
            threading.Thread(target=self.process_task, args=(e.record,), daemon=True).start()
            if e.action == 'create' and e.record.sender == 'user' else None
        )
        
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping Brain...")

if __name__ == "__main__":
    AIBrain().start()