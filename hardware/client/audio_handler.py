# client/audio_handler.py
import sounddevice as sd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioHandler:
    def __init__(self, hardware_samplerate: int = 48000, channels: int = 2, dtype: str = 'float32', volume_factor: float = 1.0):
        """
        Initialisiert den Hardware-Stream auf den stabilen Werten (48000Hz, Stereo).
        Eingehendes Gemini Audio (24000Hz) wird live hochgerechnet.
        """
        self.samplerate = hardware_samplerate  # Bleibt stabil auf 48000 für den Treiber
        self.channels = channels              # Erzwungen: 2 Kanäle
        self.dtype = dtype                    # float32 oder int16 (float32 ist flexibler für Gain)
        self.volume_factor = volume_factor
        self.output_stream: Optional[sd.OutputStream] = None
        self._initialize_output_stream()

        # Für die Steuerung der sequentiellen Audiowiedergabe
        self.next_play_time: float = 0.0 # Hält den Zeitpunkt für das nächste Audio-Chunk
        self.scheduled_sources: list = [] # Hält Referenzen zu den geplanten AudioBufferSourceNodes

    def _get_hifiberry_device_index(self) -> Optional[int]:
        if sd is None:
            logger.warning("sounddevice module not available; cannot query devices.")
            return None
        devices = sd.query_devices()
        logger.debug("Scanning available sound devices...")
        for idx, dev in enumerate(devices):
            if "snd_rpi_hifiberry_dac" in dev['name'] or "hifiberry" in dev['name'].lower():
                logger.info(f"🎯 Found I2S Speaker at device index {idx}: {dev['name']}")
                return idx
        logger.warning("⚠️ I2S Speaker (hifiberry) not found in devices. Using default device.")
        return None

    def _initialize_output_stream(self):
        logger.info("🔊 Initializing hardware audio output stream...")
        if sd is None:
            logger.warning("sounddevice module not available; audio output disabled.")
            return

        try:
            target_device = self._get_hifiberry_device_index()

            # Wir setzen blocksize, um PortAudio bei Echtzeit-Streams einen festen Puffer zu geben
            self.output_stream = sd.OutputStream(
                device=target_device,
                samplerate=self.samplerate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=1024  # Hilft gegen Ruckler und 'Underflow'-Fehler im Stream
            )
            self.output_stream.start()
            logger.info(f"✅ Audio hardware stream started: {self.samplerate}Hz, {self.channels} Ch, Mode: {self.dtype}")
            # Initialisiere next_play_time basierend auf der aktuellen Stream-Zeit
            if self.output_stream:
                self.next_play_time = self.output_stream.time
        except Exception as e:
            logger.error(f"❌ Failed to initialize hardware audio stream: {e}", exc_info=True)
            self.output_stream = None

    def play_audio(self, audio_data_bytes: bytes, incoming_samplerate: int = 24000):
        """
        Nimmt rohe 16-bit PCM Audio-Bytes von Gemini (Standard: 24000Hz),
        logged alle Metadaten detailliert, skaliert auf 48000Hz hoch,
        verdoppelt zu Stereo und wendet den Volume-Gain an.
        """
        if sd is None or self.output_stream is None:
            logger.warning("Skipping playback: Sounddevice or Output Stream is None.")
            return

        byte_length = len(audio_data_bytes)
        logger.debug(f"📥 Received chunk: {byte_length} bytes. Expected incoming samplerate: {incoming_samplerate}Hz")

        if byte_length == 0:
            logger.warning("Received empty audio chunk from stream.")
            return

        try:
            # 1. Konvertiere Bytes in NumPy int16 Array
            audio_array_int16 = np.frombuffer(audio_data_bytes, dtype=np.int16)
            samples_count = len(audio_array_int16)
            logger.debug(f"📊 Extracted {samples_count} raw int16 mono samples.")

            # 2. UPSAMPLING (Von 24000Hz auf 48000Hz)
            # Wenn Gemini 24kHz liefert und Hardware 48kHz will, verdoppeln wir einfach jedes Sample.
            if incoming_samplerate == 24000 and self.samplerate == 48000:
                audio_array_int16 = np.repeat(audio_array_int16, 2)
                logger.debug(f"📈 Upsampled chunk from 24kHz to 48kHz. New sample count: {len(audio_array_int16)}")
            elif incoming_samplerate != self.samplerate:
                logger.warning(f"⚠️ Mismatch! Incoming: {incoming_samplerate}Hz vs Hardware: {self.samplerate}Hz without handling.")

            # 3. Typkonvertierung int16 -> float32 (-1.0 bis 1.0)
            audio_float = audio_array_int16.astype(np.float32) / 32768.0

            # 4. Lautstärke anheben & sichern gegen digitales Übersteuern (Clipping)
            audio_float = np.clip(audio_float * self.volume_factor, -1.0, 1.0)

            # 5. MONO -> STEREO (2D Array [Samples, 2] bauen)
            audio_stereo = np.repeat(audio_float[:, np.newaxis], self.channels, axis=1)
            logger.debug(f"📐 Final array shape for hardware: {audio_stereo.shape} with dtype: {audio_stereo.dtype}")

            # 6. Abschicken an die Soundkarte
            # Falls das interne float32-Format im __init__ auf 'int16' steht, konvertieren wir hier zurück
            if self.dtype == 'int16':
                final_output = (audio_stereo * 32767).astype(np.int16)
                self.output_stream.write(final_output)
            else:
                self.output_stream.write(audio_stereo)

            logger.debug("🔊 Chunk successfully written to hardware buffer.")

        except Exception as e:
            logger.error(f"💥 Critical Error during stream playback processing: {e}", exc_info=True)

    # def stop_playback(self):
    #     """
    #     Stoppt sofort alle aktuell laufende und geplante Audiowiedergabe.
    #     Wird für Barge-In verwendet.
    #     """
    #     if self.output_stream:
    #         logger.info("🛑 Audio playback interrupted. Stopping current output stream.")
    #         # sounddevice.OutputStream hat keine direkte Methode, um den Puffer zu leeren oder sofort zu stoppen
    #         # außer durch das Beenden des Streams. Dies führt zu einem kurzen Re-Initialisieren,
    #         # ist aber die zuverlässigste Methode für sofortigen Stop.
    #         try:
    #             self.output_stream.stop()
    #             self.output_stream.close()
    #             logger.debug("Output stream closed for immediate stop.")
    #         except Exception as e:
    #             logger.error(f"Error while trying to stop/close output stream: {e}")
    #         finally:
    #             self.output_stream = None # Setze auf None, damit _initialize_output_stream erneut aufgerufen wird

    #         # Re-initialisiere den Stream sofort, damit er für neues Audio bereit ist
    #         self._initialize_output_stream()
    #         logger.info("Output stream re-initialized after interruption.")
    #     else:
    #         logger.debug("No active output stream to stop.")

    def stop_playback(self):
        """
        Stoppt sofort alle aktuell laufende und geplante Audiowiedergabe.
        Wird für Barge-In verwendet.
        """
        if self.output_stream:
            logger.info("🛑 Audio playback interrupted. Relying on queue flush in main.")
            # WICHTIG: KEIN self.output_stream.stop() oder .close() hier!
            # Das Verhindert den C-Level ALSA Crash.
        else:
            logger.debug("No active output stream to stop.")

    def stop_all_streams(self): # Umbenannt von stop_playback, um die neue Funktion deutlicher zu machen
        if self.output_stream:
            try:
                self.output_stream.stop()
                self.output_stream.close()
                logger.info("🛑 Audio hardware stream stopped and closed successfully.")
            except Exception as e:
                logger.error(f"Error while closing stream: {e}")
            self.output_stream = None

    def __del__(self):
        self.stop_all_streams() # Rufe die umbenannte Methode auf