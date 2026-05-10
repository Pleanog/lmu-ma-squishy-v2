import os
import time
import logging
import threading
import mimetypes
from dotenv import load_dotenv

from services.pb_service import PocketBaseService
from services.llm_service import LLMService
from services.tts_service import TTSService
from models.types import MessageRecord

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class BrainOrchestrator:
    def __init__(self):
        self.pb = PocketBaseService(
            os.getenv("PB_URL"), 
            os.getenv("PB_ADMIN_EMAIL"), 
            os.getenv("PB_ADMIN_PASS")
        )
        self.llm = LLMService(os.getenv("GEMINI_API_KEY"))
        self.tts = TTSService()

    def handle_message(self, pb_event):
        # Filter logic
        if pb_event.action != 'create': return
        if pb_event.record.sender != 'user': return

        # Convert to typed object
        record = MessageRecord.from_pb_record(pb_event.record)

        # Threaded processing
        threading.Thread(target=self._worker, args=(record,), daemon=True).start()

    def _worker(self, record: MessageRecord):
        logging.info(f"📩 Processing {record.id}")
        audio_path = None
        audio_bytes = None
        reply_audio_path = None

        try:
            # 1. Download Audio (if any)
            if record.audio:
                audio_path = self.pb.download_audio(record)
                if audio_path:
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
            
            # 2. Generate Text Reply
            # Detect mime type or default to wav
            mime = mimetypes.guess_type(audio_path)[0] if audio_path else "audio/wav"
            
            ai_text = self.llm.generate_reply(
                text=record.content,
                audio_bytes=audio_bytes,
                mime_type=mime,
                metadata=record.metadata
            )
            logging.info(f"🤖 Output: {ai_text}")

            # 3. Generate Audio Reply
            reply_audio_path = self.tts.text_to_speech(ai_text)

            # 4. Upload Result
            self.pb.upload_ai_response(
                conversation_id=record.conversation,
                text=ai_text,
                audio_path=reply_audio_path
            )

        except Exception as e:
            logging.error(f"Worker crashed: {e}")
        
        finally:
            # Cleanup
            if audio_path and os.path.exists(audio_path): os.remove(audio_path)
            if reply_audio_path and os.path.exists(reply_audio_path): os.remove(reply_audio_path)

    def start(self):
        logging.info("🧠 Brain started. Waiting for messages...")
        # Use lambda to keep the reference working as observed previously
        self.pb.subscribe_messages(lambda e: self.handle_message(e))
        
        while True: time.sleep(1)

if __name__ == "__main__":
    BrainOrchestrator().start()