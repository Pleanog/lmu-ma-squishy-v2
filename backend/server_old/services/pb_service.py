import os
import requests
import tempfile
import logging
from typing import Optional
from pocketbase import PocketBase
from models.types import MessageRecord

class PocketBaseService:
    def __init__(self, url, email, password):
        self.pb = PocketBase(url)
        self.url = url
        self.authenticate(email, password)

    def authenticate(self, email, password):
        try:
            self.pb.admins.auth_with_password(email, password)
            logging.info("✅ PocketBase Connected")
        except Exception as e:
            logging.error(f"❌ DB Auth Failed: {e}")
            raise e

    def download_audio(self, record: MessageRecord) -> Optional[str]:
        """Downloads the first audio file in the record"""
        if not record.audio: return None
        
        filename = record.audio[0] # Take first file
        url = f"{self.url}/api/files/{record.collection_id}/{record.id}/{filename}"
        headers = { "Authorization": self.pb.auth_store.token }

        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                ext = os.path.splitext(filename)[1]
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                temp.write(r.content)
                temp.close()
                return temp.name
        except Exception as e:
            logging.error(f"Download failed: {e}")
        return None

    def upload_ai_response(self, conversation_id, text, audio_path=None):
        """
        Uploads data using direct requests to avoid SDK version conflicts with 'files'
        """
        url = f"{self.url}/api/collections/messages/records"
        headers = { "Authorization": self.pb.auth_store.token }
        
        # Data fields
        data = {
            "conversation": conversation_id,
            "content": text,
            "sender": "llm",
            "status": "sent",
            "metadata": '{"generated_by": "gemini-3-flash-preview"}'
        }

        # File fields
        files = {}
        file_handle = None
        if audio_path:
            file_handle = open(audio_path, 'rb')
            files = { "audio": ("reply.mp3", file_handle) }

        try:
            # Using standard requests to handle multipart/form-data correctly
            r = requests.post(url, headers=headers, data=data, files=files)
            if r.status_code >= 400:
                logging.error(f"Upload Error {r.status_code}: {r.text}")
            else:
                logging.info("✅ Reply saved to DB")
        except Exception as e:
            logging.error(f"Upload exception: {e}")
        finally:
            if file_handle: file_handle.close()

    def subscribe_messages(self, callback_fn):
        self.pb.collection('messages').subscribe(callback_fn)