# client/audio_handler.py
import sounddevice as sd
import numpy as np
import logging
from typing import Optional
import os
# from scipy.signal import resample

logger = logging.getLogger(__name__)

class AudioHandler:
    def __init__(self, hardware_samplerate: int = 16000, channels: int = 2, dtype: str = 'float32', volume_factor: float = 1.0):
        """
        Initialisiert den Hardware-Stream auf den stabilen Werten (16000, Stereo).
        Eingehendes Gemini Audio (24000Hz) wird live hochgerechnet.
        """
        self.samplerate = 16000  # Bleibt stabil auf 16000 für den Treiber
        self.channels = channels              # Erzwungen: 2 Kanäle
        self.dtype = dtype                    # float32 oder int16 (float32 ist flexibler für Gain)
        self.volume_factor = volume_factor
        self.output_stream: Optional[sd.OutputStream] = None
        self._initialize_output_stream()

        # Für die Steuerung der sequentiellen Audiowiedergabe
        self.next_play_time: float = 0.0 # Hält den Zeitpunkt für das nächste Audio-Chunk
        self.scheduled_sources: list = [] # Hält Referenzen zu den geplanten AudioBufferSourceNodes

    # Sucht nach dem HiFiBerry DAC für den Output (Alt)
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

    # # Sucht jetzt nach dem ReSpeaker für den Output
    # def _get_respeaker_device_index(self) -> Optional[int]:
    #     #  Um die Config zu bearbeiten, die den Startart Setzt:
    #     # nano ~/.asoundrc
    #     logger.info("🎯 Using ALSA default device (ReSpeaker via plughw)")
    #     return None
    #     #  Alternativ könnten wir hier auch gezielt nach dem ReSpeaker suchen, falls er nicht als Default konfiguriert ist:
    #     # if sd is None:
    #     #     logger.warning("sounddevice module not available; cannot query devices.")
    #     #     return None
    #     # devices = sd.query_devices()
    #     # logger.debug("Scanning available sound devices...")
    #     # for idx, dev in enumerate(devices):
    #     #     if "ArrayUAC10" in dev['name'] or "ReSpeaker" in dev['name']:
    #     #         logger.info(f"🎯 Found ReSpeaker Speaker at device index {idx}: {dev['name']}")
    #     #         return idx
    #     # logger.warning("⚠️ ReSpeaker not found in devices. Using default device.")
    #     # return None

    def _get_respeaker_device_index(self) -> Optional[int]:
        if sd is None:
            logger.warning("sounddevice module not available; cannot query devices.")
            return None
            
        devices = sd.query_devices()
        logger.debug(f"Available devices: {devices}")
        
        for idx, dev in enumerate(devices):
            # Wir suchen nur noch nach dem Teilstring "ReSpeaker"
            # .get('name', '') ist sicherer, falls ein Gerät keinen Namen hat
            if "ReSpeaker" in dev.get('name', ''):
                logger.info(f"🎯 Found ReSpeaker at device index {idx}: {dev['name']}")
                return idx
                
        logger.error("❌ ReSpeaker NICHT gefunden! Hier sind alle gefundenen Geräte:")
        for idx, dev in enumerate(devices):
            logger.error(f"   Index {idx}: {dev.get('name')}")
        return None

    def _initialize_output_stream(self):
        logger.info("🔊 Initializing hardware audio output stream...")
        if sd is None:
            logger.warning("sounddevice module not available; audio output disabled.")
            return

        try:
            # target_device = self._get_hifiberry_device_index()
            target_device = self._get_respeaker_device_index()

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
        Nimmt rohe 16-bit PCM Audio-Bytes von Gemini, resampelt extrem robust 
        mit Numpy (ohne Scipy-Abstürze) auf 16000Hz und spielt sie ab.
        """
        if sd is None or self.output_stream is None:
            return

        byte_length = len(audio_data_bytes)
        if byte_length < 4:  # Ignoriere winzige Chunks (< 2 Samples), die Resampler zum Absturz bringen
            return

        try:
            # 1. Bytes → int16 PCM Array
            audio_array_int16 = np.frombuffer(audio_data_bytes, dtype=np.int16)

            # 2. RESAMPLING (24000Hz -> 16000Hz) mit Numpy Interpolation
            if incoming_samplerate != self.samplerate:
                num_samples = int(len(audio_array_int16) * self.samplerate / incoming_samplerate)
                
                if num_samples <= 0:
                    return

                # Wir strecken/stauchen die Zeitachse mathematisch (absolut crash-sicher)
                t_old = np.linspace(0, 1, len(audio_array_int16))
                t_new = np.linspace(0, 1, num_samples)
                
                # int16 zu float32 konvertieren
                audio_float = audio_array_int16.astype(np.float32) / 32768.0
                
                # Das eigentliche Resampling
                audio_resampled = np.interp(t_new, t_old, audio_float)
            else:
                audio_resampled = audio_array_int16.astype(np.float32) / 32768.0

            # 3. Volume + Clipping (Anti-Distortion)
            audio_float = np.clip(audio_resampled * self.volume_factor, -1.0, 1.0)

            # 4. MONO → STEREO
            audio_stereo = np.stack([audio_float, audio_float], axis=-1)

            # 5. OUTPUT FORMAT ANPASSUNG & PLAY
            if self.dtype == 'int16':
                final_output = (audio_stereo * 32767).astype(np.int16)
            else:
                final_output = audio_stereo.astype(np.float32)

            self.output_stream.write(final_output)

        except Exception as e:
            logger.error(f"💥 Critical error during audio playback: {e}", exc_info=True)

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