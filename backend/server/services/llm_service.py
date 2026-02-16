import logging
from google import genai
from google.genai import types

class LLMService:
    def __init__(self, api_key):
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-3-flash-preview" 
            logging.info("✨ LLM Service Ready")
        except Exception as e:
            logging.error(f"❌ LLM Init Failed: {e}")

    def build_prompt(self, metadata):
        prompt = (
            "You are a helpful, sentient hardware companion. "
            "Keep answers extremely short (max 2 sentences)."
            "If you can answer a question with yes or no, do so first. Then go into details if needed."
            "If the answer really needs to be longer than 2 sentences, you may do so."
        )
        if metadata.get('brightness') == 'low': prompt += " It is dark. Whisper."
        if metadata.get('shaken'): prompt += " URGENT: I was shaken! Be chaotic!"
        return prompt

    def generate_reply(self, text, audio_bytes=None, mime_type="audio/wav", metadata=None):
        sys_prompt = self.build_prompt(metadata or {})
        
        contents = []
        if text: contents.append(text)
        if audio_bytes:
            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type))

        if not contents: return "I heard nothing."

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt
                    
                )
            )
            return response.text
        except Exception as e:
            logging.error(f"LLM Generate Error: {e}")
            return "My brain hurts (API Error)."