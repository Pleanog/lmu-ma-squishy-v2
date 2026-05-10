import os
import random
import time
from pocketbase import PocketBase

# CONFIG
PB_URL = "http://127.0.0.1:8090"
# Login as a regular user (simulating the hardware owner)
USER_EMAIL = "user@example.com" 
USER_PASS = "12345678"

# Setup
pb = PocketBase(PB_URL)
pb.collection('users').auth_with_password(USER_EMAIL, USER_PASS)
user_id = pb.auth_store.model.id

# Get or Create a Conversation
print("Searching for conversation...")
chats = pb.collection('conversations').get_list(1, 1, {"filter": f'user="{user_id}"', "sort": "-created"})
if len(chats.items) > 0:
    chat_id = chats.items[0].id
else:
    chat = pb.collection('conversations').create({"user": user_id, "title": "Hardware Chat", "is_active": True})
    chat_id = chat.id

print(f"📱 Simulator Connected to Chat ID: {chat_id}")

# Simulation Loop
while True:
    input("Press Enter to simulate 'Hardware Activation' (Sending Audio)...")

    # 1. Random Sensors
    is_dark = random.choice([True, False])
    is_shaken = random.choice([True, False])
    
    metadata = {
        "brightness": "low" if is_dark else "normal",
        "shaken": is_shaken,
        "simulated": True
    }
    
    print(f"🎤 Sending Audio... (Sensors: Dark={is_dark}, Shaken={is_shaken})")

    # 2. Upload Audio
    # We open the file and send it
    try:
        with open("test_audio.wav", "rb") as audio_file:
            pb.collection('messages').create(
                {
                    "conversation": chat_id,
                    "content": "", # Empty text because we send audio
                    "sender": "user",
                    "metadata": metadata
                },
                files={
                    "audio": audio_file
                }
            )
        print("✅ Sent! Check the Brain terminal.")
    except FileNotFoundError:
        print("❌ Error: Please put a 'test_audio.wav' file in this folder!")