#!/usr/bin/env python3
"""
Gemini Live API Audio Streaming
Records audio from USB microphone and sends it to Gemini Live API in real-time
"""

import asyncio
import pyaudio
import logging
import sys
from datetime import datetime
from pathlib import Path
import json

# Import Gemini SDK
import google.genai as genai
from google.genai.types import LiveConnectConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Audio Configuration
SAMPLE_RATE = 16000  # Gemini Live API uses 16kHz
CHUNK_SIZE = 512     # Smaller chunks for lower latency
CHANNELS = 1         # Mono
FORMAT = pyaudio.paInt16  # 16-bit signed integers

class GeminiAudioStreamer:
    """Handles audio streaming to Gemini Live API"""
    
    def __init__(self, api_key: str, device_index: int = None):
        """
        Initialize the Gemini audio streamer
        
        Args:
            api_key: Google Gemini API key
            device_index: Audio device index (None = default)
        """
        self.api_key = api_key
        self.device_index = device_index
        self.audio_stream = None
        self.pyaudio_instance = None
        self.is_recording = False
        self.session = None
        
        # Initialize Gemini SDK
        genai.configure(api_key=api_key)
    
    def setup_audio_stream(self) -> bool:
        """Setup PyAudio stream for recording"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Get device info if specified
            if self.device_index is not None:
                device_info = self.pyaudio_instance.get_device_info_by_index(self.device_index)
                logger.info(f"Using audio device: {device_info['name']}")
            
            # Open audio stream
            self.audio_stream = self.pyaudio_instance.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=CHUNK_SIZE,
                exceptions=False
            )
            
            logger.info("✅ Audio stream initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup audio stream: {e}")
            return False
    
    async def stream_audio_to_gemini(self, duration: int = None):
        """
        Stream audio from microphone to Gemini Live API
        
        Args:
            duration: Recording duration in seconds (None = infinite)
        """
        try:
            # Create live session config
            config = LiveConnectConfig(
                response_modalities=["TEXT", "AUDIO"],
                system_prompt="You are a helpful assistant. Respond naturally and conversationally."
            )
            
            # Start live session
            logger.info("🔌 Connecting to Gemini Live API...")
            async with genai.live.aconnect(config=config) as session:
                self.session = session
                self.is_recording = True
                
                logger.info("✅ Connected to Gemini Live API")
                logger.info("🎤 Starting audio stream... (speak into microphone)")
                
                # Prepare for streaming
                if self.audio_stream is None:
                    if not self.setup_audio_stream():
                        return False
                
                chunk_count = 0
                try:
                    while self.is_recording:
                        # Check duration limit
                        if duration and chunk_count * CHUNK_SIZE / SAMPLE_RATE >= duration:
                            logger.info(f"⏱️  Duration limit reached ({duration}s)")
                            break
                        
                        # Read audio chunk from microphone
                        audio_data = self.audio_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                        
                        # Send to Gemini
                        await session.send(input=genai.live.LiveClientMessage(
                            real_time_input=genai.live.RealTimeInput(
                                media_stream=genai.live.MediaStream(
                                    mime_type="audio/pcm;rate=16000",
                                    data=audio_data
                                )
                            )
                        ))
                        
                        chunk_count += 1
                        if chunk_count % 32 == 0:  # Log every ~1 second
                            elapsed = chunk_count * CHUNK_SIZE / SAMPLE_RATE
                            logger.info(f"📤 Sent {chunk_count} chunks ({elapsed:.1f}s)")
                        
                        # Process responses
                        async for response in session.receive():
                            self._handle_gemini_response(response)
                
                except KeyboardInterrupt:
                    logger.info("\n⚠️  Stream interrupted by user")
                
                logger.info(f"✅ Streamed {chunk_count} audio chunks")
                return True
        
        except Exception as e:
            logger.error(f"❌ Error during streaming: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.is_recording = False
    
    def _handle_gemini_response(self, response):
        """Handle response from Gemini"""
        try:
            # Handle text responses
            if hasattr(response, 'text') and response.text:
                logger.info(f"🤖 Gemini: {response.text}")
            
            # Handle audio responses
            if hasattr(response, 'data') and response.data:
                logger.info(f"🔊 Gemini sent audio response ({len(response.data)} bytes)")
                # You could save or play the audio here
        
        except Exception as e:
            logger.debug(f"Note while processing response: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.is_recording = False
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        
        logger.info("✅ Cleanup complete")

async def main():
    """Main function"""
    
    # Get API key from environment
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY not found in environment variables!")
        logger.error("Please set GOOGLE_API_KEY in .env file")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Gemini Live API Audio Streaming Test")
    logger.info("=" * 60)
    
    # List audio devices
    logger.info("\nAvailable audio devices:")
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        logger.info(f"  Device {i}: {info['name']} ({info['maxInputChannels']} in)")
    p.terminate()
    
    # Get device choice
    device_choice = input("\nEnter device index (or press Enter for default): ").strip()
    device_index = int(device_choice) if device_choice.isdigit() else None
    
    # Get duration
    duration_choice = input("Recording duration in seconds (or press Enter for 30s): ").strip()
    duration = int(duration_choice) if duration_choice.isdigit() else 30
    
    logger.info(f"\nStarting stream (duration: {duration}s)...\n")
    
    # Create streamer and start
    streamer = GeminiAudioStreamer(api_key, device_index=device_index)
    
    try:
        success = await streamer.stream_audio_to_gemini(duration=duration)
        
        if success:
            logger.info("=" * 60)
            logger.info("✅ Stream test complete!")
            logger.info("=" * 60)
        else:
            sys.exit(1)
    
    finally:
        streamer.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Stream interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
