// FILE: src/utils/media-handler.ts

import { ref, watch } from 'vue';

export class MediaHandler {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioProcessor: AudioWorkletNode | ScriptProcessorNode | null = null;
  private audioSource: MediaStreamAudioSourceNode | null = null;

  // --- Audio Playback Specifics from the OLD handler ---
  private nextStartTime: number = 0;
  private scheduledSources: AudioBufferSourceNode[] = [];
  // --- END Audio Playback Specifics ---

  private videoInterval: any = null;
  private videoElement: HTMLVideoElement | null = null;
  private videoCanvas: HTMLCanvasElement | null = null;
  private videoSendCallback: ((base64: string) => void) | null = null;
  private screenShareEndedCallback: (() => void) | null = null;

  public isRecording = ref(false);
  public isCameraActive = ref(false);
  public isScreenActive = ref(false);
  public videoStream = ref<MediaStream | null>(null); // Reactive reference to the active video stream

  constructor() {
    // Watch for changes in videoStream to update isCameraActive/isScreenActive
    watch(this.videoStream, (newStream) => {
      if (!newStream) {
        this.isCameraActive.value = false;
        this.isScreenActive.value = false;
      } else {
        // Determine if it's camera or screen share based on track kind or labels
        const videoTrack = newStream.getVideoTracks()[0];
        if (videoTrack) {
          // Check for 'displaySurface' for screen share, or common camera labels
          const settings = videoTrack.getSettings();
          if (settings.displaySurface === 'monitor' || settings.displaySurface === 'window' || settings.displaySurface === 'browser') {
            this.isScreenActive.value = true;
            this.isCameraActive.value = false;
          } else { // Assume camera if not screen share
            this.isCameraActive.value = true;
            this.isScreenActive.value = false;
          }
        }
      }
    });

    // Initialize audio context on first user interaction if not already
    // This is crucial for autoplay policies.
    document.documentElement.addEventListener('click', this.initializeAudio.bind(this), { once: true });
    document.documentElement.addEventListener('keydown', this.initializeAudio.bind(this), { once: true });
  }

  // --- Audio Handling ---
  async initializeAudio(): Promise<void> {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      // Add module for AudioWorklet if not already added.
      // Assuming audio-processor.js is in /public and accessible at root path.
      try {
        await this.audioContext.audioWorklet.addModule('src/utils/audio-processor.js');
        console.log("AudioWorklet module added.");
      } catch (e) {
        console.warn("Failed to add AudioWorklet module, ScriptProcessorNode will be used for mic input:", e);
      }
    }
    // Resume context if suspended (e.g., after user interaction)
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
      console.log("AudioContext initialized/resumed.");
    }
    // Update nextStartTime for playback queue if context was suspended
    if (this.audioContext) {
      this.nextStartTime = this.audioContext.currentTime;
    }
  }

  async startAudio(onAudioData: (data: ArrayBuffer) => void): Promise<void> {
    if (this.isRecording.value) return;

    await this.initializeAudio(); // Ensure audio context is ready
    if (!this.audioContext) throw new Error("AudioContext not initialized.");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Microphone API unavailable in this browser context (use HTTPS for remote access).");
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioSource = this.audioContext!.createMediaStreamSource(this.mediaStream);

      // Check for AudioWorklet support first
      if (this.audioContext!.audioWorklet) {
        try {
          // AudioWorklet module should already be added during initializeAudio
          this.audioProcessor = new AudioWorkletNode(this.audioContext!, 'audio-processor');
          this.audioProcessor.port.onmessage = (event) => {
            // event.data will be ArrayBuffer (Int16Array.buffer) from audio-processor.js
            onAudioData(event.data);
          };
          this.audioSource.connect(this.audioProcessor);
          // Mute local feedback for mic input by connecting to a gain node with value 0
          const muteGain = this.audioContext.createGain();
          muteGain.gain.value = 0;
          this.audioProcessor.connect(muteGain);
          muteGain.connect(this.audioContext.destination);
          console.log("Using AudioWorklet for audio processing.");
        } catch (e) {
          console.warn("AudioWorklet failed, falling back to ScriptProcessorNode:", e);
          this.useScriptProcessor(onAudioData);
        }
      } else {
        console.warn("AudioWorklet not supported, falling back to ScriptProcessorNode.");
        this.useScriptProcessor(onAudioData);
      }

      this.isRecording.value = true;
      console.log("Microphone recording started.");
    } catch (err) {
      console.error('Error accessing microphone:', err);
      this.isRecording.value = false;
      throw err; // Re-throw to inform UI
    }
  }

  private useScriptProcessor(onAudioData: (data: ArrayBuffer) => void): void {
    const bufferSize = 4096; // This needs to be a power of 2
    this.audioProcessor = this.audioContext!.createScriptProcessor(bufferSize, 1, 1);
    this.audioProcessor.onaudioprocess = (event) => {
      const inputData = event.inputBuffer.getChannelData(0); // Get mono data
      const downsampledData = this.downsampleBuffer(inputData, this.audioContext!.sampleRate, 16000); // Target 16kHz
      const pcm16 = this.convertFloat32ToInt16(downsampledData); // Convert to Int16Array.buffer
      onAudioData(pcm16);
    };
    this.audioSource!.connect(this.audioProcessor);
    // Mute local feedback for mic input by connecting to a gain node with value 0
    const muteGain = this.audioContext!.createGain();
    muteGain.gain.value = 0;
    this.audioProcessor.connect(muteGain);
    muteGain.connect(this.audioContext!.destination);
    console.log("Using ScriptProcessorNode for audio processing.");
  }

  private downsampleBuffer(buffer: Float32Array, inputSampleRate: number, outputSampleRate: number): Float32Array {
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
        accum += buffer[i]!;
        count++;
      }
      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  // Helper from old handler for converting Float32Array to Int16Array.buffer
  private convertFloat32ToInt16(buffer: Float32Array): ArrayBuffer {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
      buf[l] = Math.min(1, Math.max(-1, buffer[l]!)) * 0x7fff;
    }
    return buf.buffer;
  }

  stopAudio(): void {
    if (!this.isRecording.value) return;

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.audioSource) {
      this.audioSource.disconnect();
      this.audioSource = null;
    }
    if (this.audioProcessor) {
      this.audioProcessor.disconnect();
      this.audioProcessor = null;
    }
    this.isRecording.value = false;
    console.log("Microphone recording stopped.");
  }

  // *** REPARIERTE playAudio METHODE ***
  async playAudio(arrayBuffer: ArrayBuffer): Promise<void> {
    if (!this.audioContext) {
      // We rely on the initial user interaction to initialize the context.
      // If playAudio is called before that, it will be warned, but we can't force resume.
      console.warn("AudioContext not initialized, cannot play audio. Awaiting user interaction.");
      return;
    }

    if (this.audioContext.state === "suspended") {
      console.warn("AudioContext suspended, attempting to resume for playback.");
      try {
        await this.audioContext.resume();
      } catch (e) {
        console.error("Failed to resume AudioContext:", e);
        return;
      }
    }

    const pcmData = new Int16Array(arrayBuffer); // Backend sends Int16Array.buffer
    const float32Data = new Float32Array(pcmData.length);
    for (let i = 0; i < pcmData.length; i++) {
      float32Data[i] = pcmData[i]! / 32768.0; // Convert to Float32 range [-1, 1]
    }

    // Backend sends audio/pcm;rate=24000.
    const buffer = this.audioContext.createBuffer(1, float32Data.length, 24000);
    buffer.getChannelData(0).set(float32Data);

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);

    const now = this.audioContext.currentTime;
    this.nextStartTime = Math.max(now, this.nextStartTime); // Schedule after current time or last scheduled sound
    source.start(this.nextStartTime);
    this.nextStartTime += buffer.duration; // Update next start time for sequential playback

    this.scheduledSources.push(source);
    source.onended = () => {
      const idx = this.scheduledSources.indexOf(source);
      if (idx > -1) this.scheduledSources.splice(idx, 1);
    };
  }

  // *** REPARIERTE stopAudioPlayback METHODE ***
  stopAudioPlayback(): void {
    this.scheduledSources.forEach((s) => {
      try {
        s.stop();
      } catch (e) {
        // console.warn("Error stopping audio source (might have already ended):", e);
      }
      s.disconnect(); // Ensure disconnection
    });
    this.scheduledSources = [];
    if (this.audioContext) {
      this.nextStartTime = this.audioContext.currentTime; // Reset next start time
    }
    console.log("Audio playback interrupted.");
  }

  // --- Video/Screen Sharing Handling ---
  async startVideo(videoElement: HTMLVideoElement, onVideoData: (base64: string) => void): Promise<void> {
    if (this.isCameraActive.value || this.isScreenActive.value) {
      this.stopVideo();
    }
    this.videoElement = videoElement;
    this.videoCanvas = document.createElement('canvas'); // Create canvas dynamically
    this.videoSendCallback = onVideoData;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoElement.srcObject = this.mediaStream;
      await videoElement.play();
      this.videoStream.value = this.mediaStream; // Update reactive stream
      // isCameraActive will be updated by the watch handler
      this.startVideoSender();
      console.log("Camera started.");
    } catch (err) {
      console.error('Error accessing camera:', err);
      this.isCameraActive.value = false;
      this.videoStream.value = null;
      throw err;
    }
  }

  async startScreen(
    videoElement: HTMLVideoElement,
    onVideoData: (base64: string) => void,
    onEnded: () => void
  ): Promise<void> {
    if (this.isCameraActive.value || this.isScreenActive.value) {
      this.stopVideo();
    }
    this.videoElement = videoElement;
    this.videoCanvas = document.createElement('canvas');
    this.videoSendCallback = onVideoData;
    this.screenShareEndedCallback = onEnded;

    try {
      // Request screen share with system audio if desired
      this.mediaStream = await (navigator.mediaDevices as any).getDisplayMedia({
        video: true,
        audio: false // Set to true if you want to share system audio (browser support varies)
      });
      videoElement.srcObject = this.mediaStream;
      await videoElement.play();
      this.videoStream.value = this.mediaStream; // Update reactive stream
      // isScreenActive will be updated by the watch handler
      this.startVideoSender();

      this.mediaStream!.getVideoTracks()[0]!.onended = () => {
        console.log("Screen share ended by user.");
        this.stopVideo();
        if (this.screenShareEndedCallback) {
          this.screenShareEndedCallback();
        }
      };
      console.log("Screen sharing started.");
    } catch (err) {
      console.error('Error accessing screen share:', err);
      this.isScreenActive.value = false;
      this.videoStream.value = null;
      throw err;
    }
  }

  stopVideo(): void {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.videoInterval) {
      clearInterval(this.videoInterval);
      this.videoInterval = null;
    }
    // Don't nullify videoElement, videoCanvas, videoSendCallback directly here,
    // as they might be needed by the Vue component before they're garbage collected.
    // The watch on videoStream handles reactive state.
    this.videoStream.value = null; // Clear reactive stream which triggers UI updates
    console.log("Video/Screen stream stopped.");
  }

  private startVideoSender(): void {
    if (!this.videoElement || !this.videoCanvas || !this.videoSendCallback) {
      return;
    }

    if (this.videoInterval) {
      clearInterval(this.videoInterval);
    }

    const captureFrame = () => {
      if (this.videoElement && this.videoCanvas && this.videoElement.readyState >= this.videoElement.HAVE_CURRENT_DATA) {
        const context = this.videoCanvas.getContext('2d');
        if (context) {
          this.videoCanvas.width = this.videoElement.videoWidth;
          this.videoCanvas.height = this.videoElement.videoHeight;
          context.drawImage(this.videoElement, 0, 0, this.videoCanvas.width, this.videoCanvas.height);
          const base64Data = this.videoCanvas.toDataURL('image/jpeg', 0.8).split(',')[1]; // Adjust quality as needed
          if (base64Data) {
            this.videoSendCallback!(base64Data);
          }
        }
      }
    };

    // Send a frame every 200ms (5 FPS) - adjust for desired performance/bandwidth
    this.videoInterval = setInterval(captureFrame, 200);
  }
}