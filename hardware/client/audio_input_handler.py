# client/audio_input_handler.py
import pyaudio
import numpy as np
import logging
import asyncio
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

class AudioInputHandler:
    """
    Verwaltet die Audioaufnahme von einem Mikrofon (speziell optimiert für UM10/USB-Mikrofone)
    und stellt die aufgenommenen Daten in Chunks zur Verfügung.
    """

    FORMAT = pyaudio.paInt16
    DEFAULT_RATE = 16000  # Standard-Sample-Rate für die Übertragung zum Backend (z.B. Gemini)
    # CHUNK_SIZE = 1024     # Größe des Audio-Buffers pro Lesevorgang
    CHUNK_SIZE = 4096     # Größe des Audio-Buffers pro Lesevorgang

    def __init__(self,
                 on_audio_data_callback: Callable[[bytes], Any], # Callback ist jetzt awaitable
                 target_channels: int = 1, # Wir senden Mono an Gemini
                #  device_name_keywords: list[str] = ["UM10", "USB Audio Device"],
                 device_name_keywords: list[str] = ["ArrayUAC10", "ReSpeaker"],
                 rates_to_test: list[int] = [48000, 44100, 16000, 32000]):
        """
        Initialisiert den AudioInputHandler.

        Args:
            on_audio_data_callback: Eine asynchrone Callback-Funktion, die mit den
                                    aufgenommenen Audio-Bytes aufgerufen wird.
            target_channels: Die Anzahl der Kanäle, die an das Backend gesendet werden sollen (Mono).
            device_name_keywords: Schlüsselwörter zur Identifizierung des Mikrofons.
            rates_to_test: Eine Liste von Sample-Raten, die zum Testen der Mikrofonkompatibilität verwendet werden.
        """
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.input_stream: Optional[pyaudio.Stream] = None
        self.on_audio_data_callback = on_audio_data_callback
        self.target_channels = target_channels
        self.device_name_keywords = device_name_keywords
        self.rates_to_test = rates_to_test

        self.input_device_index: Optional[int] = None
        self.native_channels: int = 1
        self.chosen_rate: int = self.DEFAULT_RATE # Die Rate, mit der das Mikro tatsächlich läuft
        self.recording_task: Optional[asyncio.Task] = None
        self._is_recording = False

    async def initialize(self) -> bool:
        """
        Initialisiert PyAudio und versucht, ein kompatibles Mikrofon zu finden
        und den Stream zu öffnen.

        Returns:
            True, wenn die Initialisierung erfolgreich war, sonst False.
        """
        logger.info("🎙️ Initialisiere AudioInputHandler...")
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # 1. Hardware suchen
            self.input_device_index, self.native_channels = self._find_input_device()
            if self.input_device_index is None:
                logger.error("❌ Kein geeignetes Mikrofon gefunden.")
                return False

            # 2. Die richtige Sample-Rate ermitteln und Stream öffnen
            self.input_stream, self.chosen_rate = self._open_input_stream()
            if self.input_stream is None:
                logger.error("❌ Konnte keinen Audio-Input-Stream öffnen.")
                return False

            dev_info = self.pyaudio_instance.get_device_info_by_index(self.input_device_index)
            logger.info(f"✅ AudioInputHandler erfolgreich initialisiert. Mikrofon: '{dev_info['name']}' @ {self.chosen_rate}Hz, {self.native_channels} Kanäle.")
            return True

        except Exception as e:
            logger.critical(f"❌ Kritischer Fehler bei der Initialisierung des AudioInputHandler: {e}", exc_info=True)
            self.terminate()
            return False

    def _find_input_device(self) -> tuple[Optional[int], int]:
        """Sucht nach einem Audio-Input-Gerät anhand von Schlüsselwörtern."""
        if not self.pyaudio_instance: return None, 1

        logger.info(f"🔍 Suche nach Input-Geräten mit Schlüsselwörtern: {self.device_name_keywords}")
        for i in range(self.pyaudio_instance.get_device_count()):
            dev_info = self.pyaudio_instance.get_device_info_by_index(i)
            if dev_info["maxInputChannels"] > 0:
                for keyword in self.device_name_keywords:
                    if keyword.lower() in dev_info["name"].lower():
                        logger.info(f"✅ Mikrofon gefunden: [{i}] {dev_info['name']} (Kanäle: {dev_info['maxInputChannels']})")
                        return i, int(dev_info["maxInputChannels"])
        return None, 1

    def _open_input_stream(self) -> tuple[Optional[pyaudio.Stream], int]:
        """Versucht, den PyAudio-Stream mit unterstützten Sample-Raten zu öffnen."""
        if not self.pyaudio_instance or self.input_device_index is None: return None, self.DEFAULT_RATE

        for rate in self.rates_to_test:
            try:
                logger.debug(f"Versuche Sample-Rate: {rate} Hz für Input-Stream...")
                stream = self.pyaudio_instance.open(
                    format=self.FORMAT,
                    channels=self.native_channels, # Native Kanäle des Mikrofons
                    rate=rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.CHUNK_SIZE
                )
                logger.info(f"🎉 Erfolg! Input-Stream geöffnet mit {rate} Hz.")
                return stream, rate
            except Exception as e:
                logger.debug(f"Fehler bei Sample-Rate {rate} Hz: {e}")
                continue
        logger.error("❌ Keine der getesteten Sample-Raten wird vom Mikrofon unterstützt.")
        return None, self.DEFAULT_RATE

    async def start_recording(self):
        """Startet die kontinuierliche Audioaufnahme in einem separaten Task."""
        if self._is_recording:
            logger.warning("Aufnahme läuft bereits.")
            return
        if self.input_stream is None:
            logger.error("Kann Aufnahme nicht starten: Input-Stream nicht initialisiert.")
            return
        if self.recording_task and not self.recording_task.done():
            logger.warning("Aufnahme-Task läuft bereits, starte nicht neu.")
            return

        self._is_recording = True
        logger.info("🎙️ Starte Audioaufnahme...")
        self.recording_task = asyncio.create_task(self._record_loop())

    async def _record_loop(self):
        """Der asynchrone Loop für die kontinuierliche Audioaufnahme."""
        if self.input_stream is None:
            logger.error("Record-Loop kann nicht starten, Stream ist None.")
            self._is_recording = False
            return

        try:
            while self._is_recording:
                raw_data = await asyncio.to_thread(
                    self.input_stream.read, self.CHUNK_SIZE, exception_on_overflow=False
                )
                
                # --- HIER IST DIE ANPASSUNG ---
                # 1. Byte-Daten in ein NumPy-Array konvertieren (16-bit)
                # Das Array hat die Form [CHUNK_SIZE, native_channels]
                audio_array = np.frombuffer(raw_data, dtype=np.int16)
                audio_array = audio_array.reshape((-1, self.native_channels))
                
                # 2. Nur Kanal 0 extrahieren (Smart Channel mit HW-Echo-Cancellation)
                # Damit ist der Loopback (Kanal 5) physikalisch komplett isoliert!
                mono_data = audio_array[:, 0]
                
                processed_data = mono_data.tobytes()
                # ------------------------------
                
                # Resampling, wenn chosen_rate != DEFAULT_RATE 
                if self.chosen_rate != self.DEFAULT_RATE:
                    downsample_factor = self.chosen_rate // self.DEFAULT_RATE
                    if downsample_factor > 1 and self.chosen_rate % self.DEFAULT_RATE == 0:
                        audio_array_full_rate = np.frombuffer(processed_data, dtype=np.int16)
                        audio_array_target_rate = audio_array_full_rate[::downsample_factor]
                        processed_data = audio_array_target_rate.tobytes()
                    else:
                        logger.warning(f"Resampling von {self.chosen_rate}Hz zu {self.DEFAULT_RATE}Hz nicht exakt oder nicht unterstützt.")
                        # Hier könnte man komplexeres Resampling einbauen oder den Stream beenden, wenn es kritisch ist

                if asyncio.iscoroutinefunction(self.on_audio_data_callback):
                    asyncio.create_task(self.on_audio_data_callback(processed_data))
                else:
                    self.on_audio_data_callback(processed_data)
                
                await asyncio.sleep(0.005)

        except asyncio.CancelledError:
            # Wird geworfen, wenn wir mit Strg+C abbrechen
            logger.info("Audioaufnahme-Task wurde abgebrochen (CancelledError).")
        except Exception as e:
            # Fängt alle anderen Fehler (z.B. wenn das USB-Kabel gezogen wird)
            logger.error(f"Unerwarteter Fehler während der Aufnahme: {e}", exc_info=True)
        finally:
            self._is_recording = False
            logger.info("🛑 Audioaufnahme-Loop beendet.")


    async def stop_recording(self):
        """Stoppt die Audioaufnahme."""
        if self._is_recording:
            logger.info("🛑 Stoppe Audioaufnahme...")
            self._is_recording = False
            if self.recording_task:
                self.recording_task.cancel()
                try:
                    await self.recording_task # Warte auf den Abschluss des Tasks
                except asyncio.CancelledError:
                    logger.debug("Audioaufnahme-Task wurde erfolgreich abgebrochen.")
                self.recording_task = None
        else:
            logger.debug("Aufnahme läuft nicht, nichts zu stoppen.") # Debug statt Warning

    def terminate(self):
        """Beendet den PyAudio-Stream und die PyAudio-Instanz."""
        logger.info("🗑️ Beende AudioInputHandler...")
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
                logger.debug("Input-Stream geschlossen.")
            except Exception as e:
                logger.error(f"Fehler beim Schließen des Input-Streams: {e}")
            finally:
                self.input_stream = None

        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
                logger.debug("PyAudio-Instanz beendet.")
            except Exception as e:
                logger.error(f"Fehler beim Beenden der PyAudio-Instanz: {e}")
            finally:
                self.pyaudio_instance = None

    def __del__(self):
        # asyncio.run(self.stop_recording()) # __del__ kann keine Coroutinen awaiten
        self.terminate()