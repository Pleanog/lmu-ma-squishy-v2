// utils/media-handler.ts
import { ref, type Ref } from 'vue'; // Import ref for reactivity

export class MediaHandler {
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;

  // Make these properties reactive for Vue component
  public videoStream: Ref<MediaStream | null> = ref(null);
  public isRecording: Ref<boolean> = ref(false);
  public isCameraActive: Ref<boolean> = ref(false); // New reactive flag for camera state
  public isScreenActive: Ref<boolean> = ref(false); // New reactive flag for screen state

  private videoInterval: number | null = null;
  private nextStartTime: number = 0;
  private scheduledSources: AudioBufferSourceNode[] = [];
  private videoCanvas: HTMLCanvasElement;
  private canvasCtx: CanvasRenderingContext2D | null;

  constructor() {
    this.videoCanvas = document.createElement("canvas");
    this.canvasCtx = this.videoCanvas.getContext("2d");

    // Initialize audio context on first user interaction if not already
    document.documentElement.addEventListener('click', this.initializeAudio.bind(this), { once: true });
    document.documentElement.addEventListener('keydown', this.initializeAudio.bind(this), { once: true });
  }

  async initializeAudio(): Promise<void> {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      // Ensure the path to pcm-processor.js is correct relative to where it's served
      // In a Vue/Vite project, 'public' or 'src/assets' might be better, or directly within utils
      await this.audioContext.audioWorklet.addModule("/src/utils/pcm-processor.js"); // Adjust path if necessary
    }
    if (this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }
  }

  async startAudio(onAudioData: (data: ArrayBuffer) => void): Promise<void> {
    await this.initializeAudio();
    if (!this.audioContext) throw new Error("AudioContext not initialized.");

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.audioWorkletNode = new AudioWorkletNode(this.audioContext, "pcm-processor");

      this.audioWorkletNode.port.onmessage = (event: MessageEvent<Float32Array>) => {
        if (this.isRecording.value) { // Access reactive value
          const downsampled = this.downsampleBuffer(
            event.data,
            this.audioContext!.sampleRate, // audioContext should be non-null here
            16000
          );
          const pcm16 = this.convertFloat32ToInt16(downsampled);
          onAudioData(pcm16);
        }
      };

      source.connect(this.audioWorkletNode);
      // Mute local feedback by connecting to a gain node with value 0
      const muteGain = this.audioContext.createGain();
      muteGain.gain.value = 0;
      this.audioWorkletNode.connect(muteGain);
      muteGain.connect(this.audioContext.destination);

      this.isRecording.value = true; // Update reactive state
    } catch (e) {
      console.error("Error starting audio:", e);
      throw e;
    }
  }

  stopAudio(): void {
    this.isRecording.value = false; // Update reactive state
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.audioWorkletNode) {
      this.audioWorkletNode.disconnect();
      this.audioWorkletNode = null;
    }
  }

  async startVideo(videoElement: HTMLVideoElement, onFrame: (base64Data: string) => void): Promise<void> {
    this.stopVideo(); // Stop any existing video stream
    try {
      this.videoStream.value = await navigator.mediaDevices.getUserMedia({ video: true }); // Update reactive state
      videoElement.srcObject = this.videoStream.value;
      this.isCameraActive.value = true; // Set camera active flag
      this.isScreenActive.value = false; // Ensure screen is not active

      this.videoInterval = window.setInterval(() => {
        this.captureFrame(videoElement, onFrame);
      }, 1000); // 1 FPS, adjust as needed for image sending
    } catch (e) {
      console.error("Error starting video:", e);
      throw e;
    }
  }

  async startScreen(videoElement: HTMLVideoElement, onFrame: (base64Data: string) => void, onEnded?: () => void): Promise<void> {
    this.stopVideo(); // Stop any existing video stream
    try {
      this.videoStream.value = await (navigator.mediaDevices as any).getDisplayMedia({ video: true }); // Update reactive state
      videoElement.srcObject = this.videoStream.value;
      this.isScreenActive.value = true; // Set screen active flag
      this.isCameraActive.value = false; // Ensure camera is not active

      // Handle stream ending (e.g. user clicks "Stop sharing" in browser UI)
      this.videoStream.value!.getVideoTracks()[0]!.onended = () => {
        this.stopVideo(); // Call stopVideo without passing element, as it's now tracked by ref
        if (onEnded) onEnded();
      };

      this.videoInterval = window.setInterval(() => {
        this.captureFrame(videoElement, onFrame);
      }, 1000); // 1 FPS, adjust as needed for image sending
    } catch (e) {
      console.error("Error starting screen share:", e);
      throw e;
    }
  }

  stopVideo(): void {
    if (this.videoStream.value) { // Access reactive value
      this.videoStream.value.getTracks().forEach((t) => t.stop());
      this.videoStream.value = null; // Clear reactive state
    }
    if (this.videoInterval) {
      clearInterval(this.videoInterval);
      this.videoInterval = null;
    }
    this.isCameraActive.value = false; // Reset flags
    this.isScreenActive.value = false;
    // The videoElement.srcObject = null; must be done in the Vue component as it holds the ref.
    // Or, if videoElement is guaranteed to be around, you could pass it to stopVideo.
    // For now, let the Vue component handle clearing the srcObject.
  }

  private captureFrame(videoElement: HTMLVideoElement, onFrame: (base64Data: string) => void): void {
    if (!this.videoStream.value || !this.canvasCtx) return; // Access reactive value

    // Ensure the video is ready before drawing
    if (videoElement.readyState < videoElement.HAVE_ENOUGH_DATA) {
      return;
    }

    this.videoCanvas.width = videoElement.videoWidth || 640;
    this.videoCanvas.height = videoElement.videoHeight || 480;
    this.canvasCtx.drawImage(videoElement, 0, 0, this.videoCanvas.width, this.videoCanvas.height);
    const base64 = this.videoCanvas.toDataURL("image/jpeg", 0.7).split(",")[1];
    if (base64) {
      onFrame(base64);
    }
  }

  async playAudio(arrayBuffer: ArrayBuffer): Promise<void> {
    if (!this.audioContext) {
      await this.initializeAudio(); // Ensure context is initialized
    }
    if (!this.audioContext) return; // Still might be null if initialize failed

    if (this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }

    const pcmData = new Int16Array(arrayBuffer);
    const float32Data = new Float32Array(pcmData.length);
    for (let i = 0; i < pcmData.length; i++) {
      float32Data[i] = pcmData[i]! / 32768.0;
    }

    // Assuming 24000 as the output sample rate from the server
    const buffer = this.audioContext.createBuffer(1, float32Data.length, 24000);
    buffer.getChannelData(0).set(float32Data);

    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);

    const now = this.audioContext.currentTime;
    this.nextStartTime = Math.max(now, this.nextStartTime);
    source.start(this.nextStartTime);
    this.nextStartTime += buffer.duration;

    this.scheduledSources.push(source);
    source.onended = () => {
      const idx = this.scheduledSources.indexOf(source);
      if (idx > -1) this.scheduledSources.splice(idx, 1);
    };
  }

  stopAudioPlayback(): void {
    this.scheduledSources.forEach((s) => {
      try {
        s.stop();
      } catch (e) {
        console.warn("Error stopping audio source:", e);
      }
    });
    this.scheduledSources = [];
    if (this.audioContext) {
      this.nextStartTime = this.audioContext.currentTime;
    }
  }

  // Utils
  private downsampleBuffer(buffer: Float32Array, sampleRate: number, outSampleRate: number): Float32Array {
    if (outSampleRate === sampleRate) return buffer;
    const ratio = sampleRate / outSampleRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0,
        count = 0;
      for (
        let i = offsetBuffer;
        i < nextOffsetBuffer && i < buffer.length;
        i++
      ) {
        accum += buffer[i]!;
        count++;
      }
      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  private convertFloat32ToInt16(buffer: Float32Array): ArrayBuffer {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
      buf[l] = Math.min(1, Math.max(-1, buffer[l]!)) * 0x7fff;
    }
    return buf.buffer;
  }
}