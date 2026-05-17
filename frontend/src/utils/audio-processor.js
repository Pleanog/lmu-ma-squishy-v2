// FILE: public/audio-processor.js

class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.bufferSize = 4096; // Accumulate samples until this size
    this.targetSampleRate = 16000; // Target sample rate for backend
  }

  // Downsample logic from MediaHandler
  downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
    if (outputSampleRate === inputSampleRate) {
      return buffer;
    }
    const sampleRateRatio = inputSampleRate / outputSampleRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
      let accum = 0, count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input.length > 0) {
      const channelData = input[0]; // Assuming mono audio
      this.buffer.push(...channelData);

      if (this.buffer.length >= this.bufferSize) {
        const fullBuffer = new Float32Array(this.buffer.slice(0, this.bufferSize));
        this.buffer = this.buffer.slice(this.bufferSize); // Keep remaining

        // Downsample before sending
        const downsampled = this.downsampleBuffer(fullBuffer, sampleRate, this.targetSampleRate);

        // Convert Float32Array to Int16Array (signed 16-bit PCM)
        // GeminiLive expects 16-bit signed PCM for audio input.
        const int16Array = new Int16Array(downsampled.length);
        for (let i = 0; i < downsampled.length; i++) {
          let s = Math.max(-1, Math.min(1, downsampled[i]));
          s = s < 0 ? s * 0x8000 : s * 0x7FFF;
          int16Array[i] = s;
        }

        this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
      }
    }
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);