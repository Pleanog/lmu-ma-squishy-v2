# squishy_pi_client/utils/audio_utils.py

import numpy as np

def downsample_audio(audio_buffer: np.ndarray, original_samplerate: int, target_samplerate: int) -> np.ndarray:
    """
    Downsamples an audio buffer from original_samplerate to target_samplerate.
    Assumes mono audio.
    """
    if original_samplerate == target_samplerate:
        return audio_buffer
    
    # Using scipy.signal.resample for better quality downsampling
    # This might require `pip install scipy`
    # For now, let's keep a simpler numpy-only approach if scipy is not installed by default
    
    # Simple averaging downsampling (less quality but no extra dependency for now)
    ratio = original_samplerate / target_samplerate
    new_length = int(len(audio_buffer) / ratio)
    
    # Use linear interpolation for better quality than simple skipping/averaging
    # Requires an x-axis for interpolation
    original_indices = np.arange(len(audio_buffer))
    target_indices = np.linspace(0, len(audio_buffer) - 1, new_length)
    
    downsampled = np.interp(target_indices, original_indices, audio_buffer)
    
    return downsampled


def float_to_int16(audio_buffer: np.ndarray) -> bytes:
    """Converts a float32 numpy array (range -1.0 to 1.0) to 16-bit PCM bytes."""
    # Ensure values are within -1 to 1
    audio_buffer = np.clip(audio_buffer, -1.0, 1.0)
    # Convert to 16-bit integers
    int16_buffer = (audio_buffer * 32767).astype(np.int16)
    return int16_buffer.tobytes()

def int16_to_float32(audio_bytes: bytes) -> np.ndarray:
    """Converts 16-bit PCM bytes to a float32 numpy array (range -1.0 to 1.0)."""
    int16_buffer = np.frombuffer(audio_bytes, dtype=np.int16)
    float32_buffer = int16_buffer.astype(np.float32) / 32767.0
    return float32_buffer