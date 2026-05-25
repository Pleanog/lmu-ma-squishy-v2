import pyaudio
import wave

FORMAT = pyaudio.paInt16
CHUNK = 1024
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "test_output.wav"

p = pyaudio.PyAudio()

# 1. Hardware suchen
input_device_index = None
native_channels = 1

print("🔍 Suche nach UM10...")
for i in range(p.get_device_count()):
    dev_info = p.get_device_info_by_index(i)
    if "UM10" in dev_info["name"] or "USB" in dev_info["name"]:
        if dev_info["maxInputChannels"] > 0:
            input_device_index = i
            native_channels = int(dev_info["maxInputChannels"])
            print(f"✅ Gefunden: [{i}] {dev_info['name']} (Standard-Kanäle: {native_channels})")
            break

if input_device_index is None:
    print("❌ UM10 wurde nicht gefunden. Bitte mit 'arecord -l' prüfen.")
    p.terminate()
    exit(1)

# 2. Die richtige Sample-Rate ermitteln
# Wir testen die typischen Hardware-Raten durch
rates_to_test = [48000, 44100, 16000, 32000]
stream = None
chosen_rate = None

for rate in rates_to_test:
    try:
        print(f"Versuche Sample-Rate: {rate} Hz...")
        stream = p.open(format=FORMAT,
                        channels=native_channels,
                        rate=rate,
                        input=True,
                        input_device_index=input_device_index,
                        frames_per_buffer=CHUNK)
        chosen_rate = rate
        print(f"🎉 Erfolg! Stream geöffnet mit {rate} Hz.")
        break
    except Exception:
        continue

if stream is None:
    print("❌ Keine der üblichen Sample-Raten (48k, 44.1k, 16k) wird von der Hardware unterstützt.")
    p.terminate()
    exit(1)

# 3. Aufnahme starten
print(f"🎙️ Aufnahme startet für {RECORD_SECONDS} Sekunden... Bitte sprich ins Mikrofon.")

frames = []
for i in range(0, int(chosen_rate / CHUNK * RECORD_SECONDS)):
    try:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    except Exception as e:
        print(f"Fehler während der Aufnahme: {e}")
        break

print("🛑 Aufnahme beendet.")

stream.stop_stream()
stream.close()
p.terminate()

# 4. Datei schreiben
wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(native_channels)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(chosen_rate)
wf.writeframes(b''.join(frames))
wf.close()

print(f"💾 Datei erfolgreich als '{WAVE_OUTPUT_FILENAME}' gespeichert.")
print("Du kannst sie jetzt mit 'aplay test_output.wav' oder einem Player deiner Wahl testen.")