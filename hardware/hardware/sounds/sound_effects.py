from pathlib import Path

BASE_DIR = Path(__file__).parent

SOUND_EFFECTS = {
    "error": str(BASE_DIR / "zapsplat_multimedia_ui_tone_negative_error_delayed_fast_114388.wav"),
    "notification": str(BASE_DIR / "master_of_dreams_success_sound_1_748.wav"),
    "happy": str(BASE_DIR / "master_of_dreams_rise_up_594.wav"),
    "annoyed": str(BASE_DIR / "zapsplat_animals_bird_ringneck_parakeet_kiss_long_109599.wav"),
}

# Use this simple ffmpeg command to convert and normalize all audio files to 16-bit PCM WAV format at 48kHz, which is ideal for playback on the Raspberry Pi with the HiFiBerry DAC:
# for f in *.mp3; do
#     ffmpeg -i "$f" \
#       -af "loudnorm,volume=0.25" \
#       "${f%.mp3}.wav"
