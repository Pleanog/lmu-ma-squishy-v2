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


# import os
# import io
# import logging
# from abc import ABC, abstractmethod

# # For gTTS
# from gtts import gTTS

# # For Gemini TTS (Google Cloud Text-to-Speech)
# from google.cloud import texttospeech_v1 as texttospeech
# from google.oauth2 import service_account

# class AbstractTTS(ABC):
#     """Abstract base class for all TTS services."""

#     @abstractmethod
#     def text_to_speech(self, text: str, output_filename: str = "output.mp3") -> str:
#         """
#         Converts text to speech and saves it to a file.

#         Args:
#             text: The text to convert.
#             output_filename: The name of the file to save the audio to.

#         Returns:
#             The path to the saved audio file.
#         """
#         pass

# class GTTS(AbstractTTS):
#     """gTTS implementation for text-to-speech."""

#     def __init__(self):
#         logging.info("Initializing gTTS service.")

#     def text_to_speech(self, text: str, output_filename: str = "output.mp3") -> str:
#         """
#         Converts text to speech using gTTS.
#         """
#         try:
#             tts = gTTS(text=text, lang='en') # You might want to make lang configurable
#             output_path = os.path.join(os.getcwd(), output_filename)
#             tts.save(output_path)
#             logging.info(f"gTTS audio saved to {output_path}")
#             return output_path
#         except Exception as e:
#             logging.error(f"Error in gTTS: {e}")
#             raise

# class GeminiTTS(AbstractTTS):
#     """Google Cloud Text-to-Speech (Gemini TTS) implementation."""

#     def __init__(self):
#         logging.info("Initializing Gemini TTS service.")
        
#         # Load credentials from GOOGLE_APPLICATION_CREDENTIALS env var
#         credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#         if not credentials_path or not os.path.exists(credentials_path):
#             logging.warning(
#                 "GOOGLE_APPLICATION_CREDENTIALS not set or file not found. "
#                 "Gemini TTS might fail without proper authentication."
#             )
#             self._client = texttospeech.TextToSpeechClient()
#         else:
#             credentials = service_account.Credentials.from_service_account_file(credentials_path)
#             self._client = texttospeech.TextToSpeechClient(credentials=credentials)

#     def text_to_speech(self, text: str, output_filename: str = "output.mp3") -> str:
#         """
#         Converts text to speech using Google Cloud Text-to-Speech (Gemini TTS).
#         """
#         try:
#             synthesis_input = texttospeech.SynthesisInput(text=text)

#             # Select the voice and audio file type
#             # You can customize these parameters based on your needs
#             # For Gemini TTS, you might use 'en-US-Neural2-C' or similar,
#             # but for a generic setup, 'en-US-Wavenet-D' is a good starting point.
#             # Refer to: https://cloud.google.com/text-to-speech/docs/voices
#             voice = texttospeech.VoiceSelectionParams(
#                 language_code="en-US",
#                 name="en-US-Neural2-C", # Example voice. Check available voices.
#             )

#             audio_config = texttospeech.AudioConfig(
#                 audio_encoding=texttospeech.AudioEncoding.MP3,
#                 # You can adjust pitch, speaking_rate here if needed
#             )

#             response = self._client.synthesize_speech(
#                 input=synthesis_input, voice=voice, audio_config=audio_config
#             )

#             output_path = os.path.join(os.getcwd(), output_filename)
#             with open(output_path, "wb") as out:
#                 out.write(response.audio_content)
#                 logging.info(f"Gemini TTS audio saved to {output_path}")
#             return output_path

#         except Exception as e:
#             logging.error(f"Error in Gemini TTS: {e}")
#             raise

# class TTSService:
#     """
#     Service to manage different TTS providers.
#     """
#     def __init__(self):
#         self._tts_providers = {
#             "gtts": GTTS(),
#             "gemini": GeminiTTS(),
#             # Add other TTS providers here
#         }
#         # Set a default provider
#         self._current_provider_name = "gtts"
#         self._current_provider = self._tts_providers[self._current_provider_name]
#         logging.info(f"Default TTS provider set to: {self._current_provider_name}")

#     def set_provider(self, provider_name: str):
#         """Sets the active TTS provider."""
#         if provider_name not in self._tts_providers:
#             raise ValueError(f"Unknown TTS provider: {provider_name}. Available: {list(self._tts_providers.keys())}")
#         self._current_provider_name = provider_name
#         self._current_provider = self._tts_providers[provider_name]
#         logging.info(f"TTS provider switched to: {self._current_provider_name}")

#     def text_to_speech(self, text: str, output_filename: str = "output.mp3", provider_name: str = None) -> str:
#         """
#         Converts text to speech using the specified or current provider.

#         Args:
#             text: The text to convert.
#             output_filename: The name of the file to save the audio to.
#             provider_name: (Optional) The name of the provider to use for this call.
#                            If None, the currently set provider will be used.

#         Returns:
#             The path to the saved audio file.
#         """
#         if provider_name:
#             if provider_name not in self._tts_providers:
#                 raise ValueError(f"Unknown TTS provider: {provider_name}. Available: {list(self._tts_providers.keys())}")
#             provider = self._tts_providers[provider_name]
#         else:
#             provider = self._current_provider
        
#         return provider.text_to_speech(text, output_filename)