# Der Speaker Test klappt:
# speaker-test -D hw:2,0 -c2 -t wav
try:
    import sounddevice as sd
except Exception:  # sounddevice may be unavailable in some environments
    sd = None
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioHandler:
    def __init__(self, samplerate: int = 48000, channels: int = 2, dtype: str = 'float32', volume_factor: float = 2.5):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.volume_factor = volume_factor  # Multiplikator für die Lautstärke (z.B. 1.0 = normal, 2.5 = lauter)
        self.output_stream = None
        self._initialize_output_stream()

    def _get_hifiberry_device_index(self) -> Optional[int]:
        """Sucht automatisch nach dem Index der I2S-Soundkarte."""
        if sd is None:
            return None
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            # Wir suchen nach dem Treibernamen deiner Card 2
            if "snd_rpi_hifiberry_dac" in dev['name'] or "hifiberry" in dev['name'].lower():
                logger.info(f"Found I2S Speaker at device index {idx}: {dev['name']}")
                return idx
        logger.warning("I2S Speaker (hifiberry) not found in devices. Falling back to default device.")
        return None

    def _initialize_output_stream(self):
        logger.info("🔊 Initializing audio output stream...")
        if sd is None:
            logger.warning("sounddevice module not available; audio output disabled.")
            self.output_stream = None
            return

        try:
            # Automatisch das richtige Device ermitteln
            target_device = self._get_hifiberry_device_index()

            # Falls target_device None ist, nutzt sounddevice automatisch das System-Standardgerät
            self.output_stream = sd.OutputStream(
                device=target_device,
                samplerate=self.samplerate,
                channels=self.channels,
                dtype=self.dtype
            )
            self.output_stream.start()
            logger.info(f"Audio output stream initialized successfully with samplerate={self.samplerate}, channels={self.channels}, dtype={self.dtype}.")
        except Exception as e:
            logger.error(f"Failed to initialize audio output stream: {e}")
            self.output_stream = None

    def play_audio(self, audio_data_bytes: bytes):
        """
        Spielt rohe 16-bit PCM Audio-Bytes ab.
        Verdoppelt die Kanäle für das Stereo-Erfordernis der Hardware und erhöht die Lautstärke.
        """
        if sd is None or self.output_stream is None:
            return

        try:
            # 1. Konvertiere Bytes in ein flaches int16 Array
            audio_array = np.frombuffer(audio_data_bytes, dtype=np.int16)

            # 2. int16 -> float32 (-1.0 bis 1.0)
            audio_float = audio_array.astype(np.float32) / 32768.0

            # 3. LAUTSTÄRKE ERHÖHEN (Digital Gain)
            # Clip sorgt dafür, dass die Wellenform bei extremer Lautstärke sauber gedeckelt wird
            audio_float = np.clip(audio_float * self.volume_factor, -1.0, 1.0)

            # 4. MONO -> STEREO 
            # Da von der API ein flaches 1D-Array kommt, machen wir daraus 2 Spalten (Links/Rechts)
            audio_stereo = np.repeat(audio_float[:, np.newaxis], 2, axis=1)

            # An den Stream übergeben
            self.output_stream.write(audio_stereo)

        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    def stop_playback(self):
        if self.output_stream:
            try:
                self.output_stream.stop()
                self.output_stream.close()
            except Exception:
                pass
            self.output_stream = None
            logger.info("Audio playback stopped and stream closed.")

    def __del__(self):
        self.stop_playback()


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)

    if sd is not None:
        print("--- Verfügbare Audio-Geräte ---")
        print(sd.query_devices())
        print("--------------------------------")

    logger.info("Starting AudioHandler test...")

    # Hier kannst du beim Erstellen direkt die Wunschlautstärke mitgeben (z.B. volume_factor=3.0)
    audio_handler = AudioHandler(volume_factor=0.5)

    # 1 Sekunde Sinus-Ton erzeugen
    duration = 2.0  # Sekunden testweise auf 2 Sek erhöht
    frequency = 440  # Hz (Kammerton A)

    t = np.linspace(
        0,
        duration,
        int(audio_handler.samplerate * duration),
        endpoint=False
    )

    # Sinus generieren
    audio_wave = 0.5 * np.sin(2 * np.pi * frequency * t)

    # Zu int16 PCM konvertieren
    audio_int16 = (audio_wave * 32767).astype(np.int16)

    # Bytes erzeugen
    audio_bytes = audio_int16.tobytes()

    logger.info("Playing test tone through I2S Speaker...")
    audio_handler.play_audio(audio_bytes)

    # Warten bis Ton fertig ist
    time.sleep(duration + 0.5)

    audio_handler.stop_playback()
    logger.info("Audio test complete.")