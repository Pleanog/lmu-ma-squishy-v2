import unittest
import os
from dotenv import load_dotenv
from services.llm_service import LLMService
from services.tts_service import TTSService

load_dotenv()

class TestComponents(unittest.TestCase):
    
    def test_tts(self):
        print("\nTesting TTS...")
        service = TTSService()
        path = service.text_to_speech("Hello testing")
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))
        print(f"✅ TTS Generated: {path}")
        os.remove(path)

    def test_llm_text_only(self):
        print("\nTesting LLM (Text)...")
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            print("⚠️ Skipping LLM test (No Key)")
            return
            
        service = LLMService(key)
        reply = service.generate_reply("Say 'Apple'", metadata={})
        print(f"✅ LLM Reply: {reply}")
        self.assertIn("Apple", reply)

if __name__ == '__main__':
    unittest.main()