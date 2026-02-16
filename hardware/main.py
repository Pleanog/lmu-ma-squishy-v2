import time
import logging
import os
from dotenv import load_dotenv

from modules.network import NetworkClient
from modules.sensors import SensorManager
from modules.audio import AudioManager

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

class SquishyHardware:
    def __init__(self):
        # 1. Init Modules
        self.sensors = SensorManager()
        self.audio = AudioManager()
        self.pb = NetworkClient(
            os.getenv("PB_URL"),
            os.getenv("HARDWARE_USER_EMAIL"),
            os.getenv("HARDWARE_USER_PASS")
        )

    def on_ai_reply(self, record):
        """Callback when AI replies"""
        if record.audio:
            logging.info("main      | 📨 Received AI Voice!")
            url = self.pb.download_file(record, record.audio)
            self.audio.play_audio(url)
        else:
            logging.info(f"main      | 📨 Received Text: {record.content}")

    def run(self):
        print("-------------------------------------")
        print("🤖 SQUISHY HARDWARE CLIENT (SIMULATION)")
        print("-------------------------------------")

        # Start Services
        self.sensors.start_simulation()
        # self.pb.connect()
        self.pb.listen_for_reply(self.on_ai_reply)

        print("\n--> Press [ENTER] to simulate 'Picking Up / Wake Word'")
        print("--> Press [CTRL+C] to stop\n")

        try:
            while True:
                # This input() blocks the loop, simulating "Waiting for Wake Word"
                input() 
                
                print("\n--- Interaction Started ---")
                
                # 1. Capture State
                current_meta = self.sensors.get_metadata()
                logging.info(f"main      | 📸 Sensor Snapshot: {current_meta}")

                # 2. Record Audio
                # (In simulation, this just grabs the test file)
                audio_file = self.audio.record_audio()

                # 3. Send
                if audio_file:
                    self.pb.upload_message(audio_file, current_meta)
                
                print("--- Waiting for Reply ---\n")

        except KeyboardInterrupt:
            print("\n👋 Shutting down...")

if __name__ == "__main__":
    SquishyHardware().run()