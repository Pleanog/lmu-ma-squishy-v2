import requests
import logging
from pocketbase import PocketBase

class NetworkClient:
    def __init__(self, url, email, password):
        self.pb = PocketBase(url)
        self.url = url
        self.authenticate(email, password)
        self.user_email = email
        self.active_chat_id = None

    def authenticate(self, email, password):
        try:
            self.pb.admins.auth_with_password(email, password)
            logging.info(f"✅ PocketBase Connected for user {self.user_email}")
            self._find_or_create_chat()
        except Exception as e:
            logging.error(f"❌ DB Auth Failed: {e}")
            raise e

    def connect(self):
        """Log in as the Hardware User"""
        try:
            auth_data = self.pb.collection('users').auth_with_password(self.email, self.password)
            self.user_email = self.pb.auth_store.model.id
            logging.info(f"network   | ✅ Connected as User: {self.user_email}")
            self._find_or_create_chat()
        except Exception as e:
            logging.error(f"network   | ❌ Connection Failed: {e}")

    def _find_or_create_chat(self):
        """Finds the active conversation for this user"""
        try:
            chats = self.pb.collection('conversations').get_list(1, 1, {
                "filter": f'user="{self.user_email}"', 
                "sort": "-created"
            })
            if len(chats.items) > 0:
                self.active_chat_id = chats.items[0].id
            else:
                new_chat = self.pb.collection('conversations').create({
                    "user": self.user_email, 
                    "title": "Hardware Chat", 
                    "is_active": True
                })
                self.active_chat_id = new_chat.id
            logging.info(f"network   | 💬 Active Chat ID: {self.active_chat_id}")
        except Exception as e:
            logging.error(f"network   | ❌ Chat Init Failed: {e}")

    def upload_message(self, audio_path, metadata):
        """Uploads Audio + Sensor Data"""
        logging.info("trying upload")
        if not self.active_chat_id: return

        logging.info("network   | 📤 Uploading voice message...")
        try:
            # We use the internal client or requests logic here
            with open(audio_path, "rb") as f:
                self.pb.collection('messages').create(
                    {
                        "conversation": self.active_chat_id,
                        "content": "", # Empty text, audio only
                        "sender": "user",
                        "metadata": metadata
                    },
                    files={ "audio": f }
                )
        except Exception as e:
            logging.error(f"network   | ❌ Upload Error: {e}")

    def listen_for_reply(self, callback_fn):
        """Subscribes to NEW messages in the active chat"""
        def on_event(e):
            if e.action == 'create' and e.record.sender == 'ai' and e.record.conversation == self.active_chat_id:
                callback_fn(e.record)
        
        self.pb.collection('messages').subscribe(on_event)
        logging.info("network   | 👂 Listening for AI replies...")
    
    def download_file(self, record, filename):
        """Helper to get the AI audio URL"""
        return f"{self.url}/api/files/{record.collection_id}/{record.id}/{filename}"