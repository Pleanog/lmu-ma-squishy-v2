# utils/audio_utils.py
import numpy as np

def downsample_audio(audio_buffer: np.ndarray, original_samplerate: int, target_samplerate: int) -> np.ndarray:
    if original_samplerate == target_samplerate:
        return audio_buffer
    
    # Simple averaging downsampling for demonstration
    # For higher quality, consider scipy.signal.resample or librosa.resample
    ratio = original_samplerate // target_samplerate
    if ratio == 0: # Upsampling case, not typical for input
        return audio_buffer # Or handle interpolation
        
    downsampled = audio_buffer[::ratio]
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