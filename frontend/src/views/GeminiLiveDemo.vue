<template>
  <div class="p-4 flex justify-content-center">
    <Card class="gemini-live-card">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <h1>Gemini Live API Demo</h1>
          <div class="flex align-items-center gap-2">
            <Tag :value="status" :severity="statusSeverity" />
          </div>
        </div>
      </template>
      <template #content>
        <!-- Authentication Section -->
        <div v-if="!isConnected && !sessionEnded" class="p-4 bg-gray-100 border-round text-center">
          <div class="mb-4 p-3 bg-white border-round text-left">
            <h3 class="mt-0 mb-2">Features Enabled:</h3>
            <ul class="ml-4 mb-3 p-0 list-disc">
              <li><strong>Native Audio:</strong> Low latency voice interaction</li>
              <li><strong>Multilingual:</strong> Speak in different languages</li>
            </ul>
            <p class="text-sm text-color-secondary">
              <em>Note: When you connect, the app sends a text message to Gemini instructing it to introduce itself and these features.</em>
            </p>
          </div>
          <p class="mb-3">Click below to connect.</p>
          <Button label="Connect" icon="pi pi-bolt" :loading="connectLoading" @click="handleConnect" />
        </div>

        <!-- Session Ended Section -->
        <div v-if="sessionEnded" class="p-5 bg-gray-50 border-round text-center fadein animation-duration-500">
          <h2 class="mt-0 mb-3">Session Ended</h2>
          <Button label="Start New Session" icon="pi pi-refresh" @click="resetUI" />
        </div>

        <!-- Application Section -->
        <div v-if="isConnected && !sessionEnded" class="app-grid">
          <div class="left-panel">
            <div class="video-container bg-black-alpha-90 border-round mb-3">
              <div v-if="showVideoPlaceholder" class="video-placeholder flex align-items-center justify-content-center text-white text-xl">
                Start camera to send video
              </div>
              <video ref="videoPreview" autoplay playsinline muted class="w-full h-full object-fit-cover"></video>
              <canvas ref="videoCanvas" style="display: none;"></canvas>
            </div>

            <div class="flex flex-wrap gap-3 mb-3">
              <Button
                :label="mediaHandler.isRecording.value ? 'Stop Mic' : 'Start Mic'"
                :icon="mediaHandler.isRecording.value ? 'pi pi-microphone-slash' : 'pi pi-microphone'"
                :severity="mediaHandler.isRecording.value ? 'danger' : undefined"
                @click="toggleMic"
              />
              <Button
                :label="mediaHandler.videoStream.value && mediaHandler.isCameraActive.value ? 'Stop Camera' : 'Start Camera'"
                :icon="mediaHandler.videoStream.value && mediaHandler.isCameraActive.value ? 'pi pi-video-slash' : 'pi pi-video'"
                :severity="mediaHandler.videoStream.value && mediaHandler.isCameraActive.value ? 'danger' : undefined"
                @click="toggleCamera"
              />
              <Button
                :label="mediaHandler.videoStream.value && mediaHandler.isScreenActive.value ? 'Stop Sharing' : 'Share Screen'"
                :icon="mediaHandler.videoStream.value && mediaHandler.isScreenActive.value ? 'pi pi-desktop' : 'pi pi-share-alt'"
                :severity="mediaHandler.videoStream.value && mediaHandler.isScreenActive.value ? 'danger' : undefined"
                @click="toggleScreenShare"
              />
              <Button label="Disconnect" icon="pi pi-times" severity="danger" @click="handleDisconnect" />
            </div>
          </div>

          <div class="right-panel flex flex-column">
            <div class="chat-log p-3 bg-gray-50 border-round overflow-y-auto mb-3 flex-grow-1" ref="chatLogRef">
              <div v-for="(msg, index) in chatMessages" :key="index" :class="['message', msg.type, { 'fadein': true, 'animation-duration-300': true }]">
                {{ msg.text }}
              </div>
            </div>
            <div class="flex gap-2">
              <InputText v-model="textInput" placeholder="Type a message..." class="flex-grow" @keyup.enter="sendText" />
              <Button label="Send" icon="pi pi-send" @click="sendText" />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Tag from 'primevue/tag';
import { MediaHandler } from './../utils/media-handler';
import { GeminiClient } from './../utils/gemini-client';

// Reactive state
const wsUrl = ref('ws://127.0.0.1:8000/ws');
const status = ref('Disconnected');
const isConnected = ref(false);
const connectLoading = ref(false);
const sessionEnded = ref(false);
const textInput = ref('');
const chatMessages = ref<{ type: 'user' | 'gemini'; text: string }[]>([]);

// Template refs
const videoPreview = ref<HTMLVideoElement | null>(null);
const videoCanvas = ref<HTMLCanvasElement | null>(null);
const chatLogRef = ref<HTMLElement | null>(null);

// Utility instances
const mediaHandler = new MediaHandler();
let geminiClient: GeminiClient;

// Computed properties for UI
const statusSeverity = computed(() => {
  if (status.value === 'Connected') return 'success';
  if (status.value === 'Disconnected') return 'info';
  if (status.value === 'Connection Error') return 'danger';
  return 'warning';
});

const showVideoPlaceholder = computed(() => {
  return !mediaHandler.videoStream.value;
});

// Message handling
let currentGeminiMessageIndex: number | null = null;
let currentUserMessageIndex: number | null = null;

function appendMessage(type: 'user' | 'gemini', text: string) {
  chatMessages.value.push({ type, text });
  scrollToChatBottom();
  return chatMessages.value.length - 1; // Return index for updates
}

function updateMessage(index: number, newText: string) {
  if (chatMessages.value[index]) {
    chatMessages.value[index].text += newText;
    scrollToChatBottom();
  }
}

function scrollToChatBottom() {
  nextTick(() => {
    if (chatLogRef.value) {
      chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight;
    }
  });
}

function handleJsonMessage(msg: any) {
  if (msg.type === "interrupted") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.type === "turn_complete") {
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.type === "user") {
    if (currentUserMessageIndex !== null) {
      updateMessage(currentUserMessageIndex, msg.text);
    } else {
      currentUserMessageIndex = appendMessage("user", msg.text);
    }
  } else if (msg.type === "gemini") {
    if (currentGeminiMessageIndex !== null) {
      updateMessage(currentGeminiMessageIndex, msg.text);
    } else {
      currentGeminiMessageIndex = appendMessage("gemini", msg.text);
    }
  }
}

// WebSocket Callbacks for GeminiClient
const geminiClientCallbacks = {
  onOpen: () => {
    status.value = "Connected";
    isConnected.value = true;
    sessionEnded.value = false;
    connectLoading.value = false;

    // Send hidden instruction
    geminiClient.sendText(
      `System: Introduce yourself as a demo of the Gemini Live API.
       Suggest playing with features like the native audio for accents and multilingual support.
       Keep the intro concise and friendly.`
    );
  },
  onMessage: (event: MessageEvent) => {
    if (typeof event.data === "string") {
      try {
        const msg = JSON.parse(event.data);
        handleJsonMessage(msg);
      } catch (e) {
        console.error("Parse error:", e);
      }
    } else {
      mediaHandler.playAudio(event.data);
    }
  },
  onClose: (e: CloseEvent) => {
    console.log("WS Closed:", e);
    status.value = "Disconnected";
    isConnected.value = false;
    showSessionEnd();
  },
  onError: (e: Event) => {
    console.error("WS Error:", e);
    status.value = "Connection Error";
    isConnected.value = false;
  },
};

// UI Control Handlers
async function handleConnect() {
  connectLoading.value = true;
  status.value = "Connecting...";

  try {
    await mediaHandler.initializeAudio(); // Initialize audio context on user gesture
    geminiClient = new GeminiClient({ wsUrl: wsUrl.value, ...geminiClientCallbacks });
    geminiClient.connect();
  } catch (error: any) {
    console.error("Connection error:", error);
    status.value = "Connection Failed: " + error.message;
    connectLoading.value = false;
  }
}

function handleDisconnect() {
  if (geminiClient) {
    geminiClient.disconnect();
  }
}

async function toggleMic() {
  if (mediaHandler.isRecording.value) {
    mediaHandler.stopAudio();
  } else {
    try {
      await mediaHandler.startAudio((data) => {
        if (geminiClient && geminiClient.isConnected()) {
          geminiClient.send(data);
        }
      });
    } catch (e) {
      alert("Could not start audio capture");
    }
  }
}

async function toggleCamera() {
  if (mediaHandler.videoStream.value && mediaHandler.isCameraActive.value) {
    mediaHandler.stopVideo();
  } else {
    // If another stream is active (e.g. Screen), stop it first
    if (mediaHandler.videoStream.value) {
      mediaHandler.stopVideo();
    }

    try {
      await mediaHandler.startVideo(videoPreview.value!, videoCanvas.value!, (base64Data) => {
        if (geminiClient && geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      });
    } catch (e) {
      alert("Could not access camera");
    }
  }
}

async function toggleScreenShare() {
  if (mediaHandler.videoStream.value && mediaHandler.isScreenActive.value) {
    mediaHandler.stopVideo();
  } else {
    // If another stream is active (e.g. Camera), stop it first
    if (mediaHandler.videoStream.value) {
      mediaHandler.stopVideo();
    }

    try {
      await mediaHandler.startScreen(
        videoPreview.value!,
        videoCanvas.value!,
        (base64Data) => {
          if (geminiClient && geminiClient.isConnected()) {
            geminiClient.sendImage(base64Data);
        }
        },
        () => {
          // onEnded callback (e.g. user stopped sharing from browser)
          mediaHandler.stopVideo(); // Ensure video state is reset
        }
      );
    } catch (e) {
      alert("Could not share screen");
    }
  }
}

function sendText() {
  const text = textInput.value;
  if (text && geminiClient && geminiClient.isConnected()) {
    geminiClient.sendText(text);
    appendMessage("user", text);
    textInput.value = "";
  }
}

function resetUI() {
  isConnected.value = false;
  sessionEnded.value = false;
  connectLoading.value = false;
  status.value = "Disconnected";
  chatMessages.value = [];
  textInput.value = '';

  mediaHandler.stopAudio();
  mediaHandler.stopVideo();

  if (geminiClient) {
    geminiClient.disconnect(); // Ensure internal client state is reset
  }
}

function showSessionEnd() {
  sessionEnded.value = true;
  mediaHandler.stopAudio();
  mediaHandler.stopVideo();
}

// Lifecycle Hooks
onMounted(() => {
  // Initialize GeminiClient here to ensure wsUrl is reactive and available if it were to change.
  // However, for this example, we re-initialize on `connect`.
});

onUnmounted(() => {
  if (geminiClient) {
    geminiClient.disconnect();
  }
  mediaHandler.stopAudio();
  mediaHandler.stopVideo();
});
</script>

<style scoped>
/* PrimeVue specific overrides and component styling */
.gemini-live-card {
  max-width: 1200px;
  width: 100%;
}

.p-card .p-card-content {
  padding-top: 0;
}

.video-container {
  aspect-ratio: 16/9;
  position: relative;
}

.video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  background-color: var(--surface-900); /* PrimeVue dark surface */
}

video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-log {
  min-height: 200px; /* Adjust as needed */
  max-height: 400px; /* Limit height and allow scrolling */
  border: 1px solid var(--surface-200);
}

.message {
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius-xl); /* Use PrimeVue variable for rounded corners */
  max-width: 80%;
  word-wrap: break-word;
  margin-bottom: 0.5rem;
  animation: fadeIn 0.3s ease-in-out;
}

.message.user {
  margin-left: auto; /* Align to right */
  background-color: var(--primary-color); /* PrimeVue primary color */
  color: var(--primary-color-text);
  border-bottom-right-radius: var(--border-radius-sm); /* Slightly sharper corner */
}

.message.gemini {
  margin-right: auto; /* Align to left */
  background-color: var(--surface-100); /* PrimeVue light surface */
  color: var(--text-color);
  border-bottom-left-radius: var(--border-radius-sm); /* Slightly sharper corner */
}

.app-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: start;
}

@media (max-width: 991px) { /* PrimeVue breakpoint for medium devices */
  .app-grid {
    grid-template-columns: 1fr;
  }
}

/* Base styles from your CSS, adapted for PrimeVue where possible */
:root {
  --primary-color: var(--primevue-primary-color, #1a73e8); /* Fallback to original if not set */
  --primary-hover: #1557b0; /* Keep original hover */
  --danger-color: #ea4335;
  --bg-color: var(--surface-0); /* PrimeVue surface background */
  --surface-color: var(--surface-ground); /* PrimeVue ground surface */
  --text-primary: var(--text-color);
  --text-secondary: var(--text-color-secondary);
  --border-color: var(--surface-200);
  --shadow-sm: var(--surface-shadow); /* Use PrimeVue shadow variables */
  --radius-md: var(--border-radius);
  --radius-lg: var(--border-radius-xl);
}

/* Adjusting padding and margins for PrimeVue */
.p-button {
  padding: 0.75rem 1.5rem;
  border-radius: var(--border-radius);
}

.p-inputtext {
  padding: 0.75rem;
  border-radius: var(--border-radius);
}

/* Specific styles for sections */
.session-end-section, .auth-section > div:first-child {
  background: var(--surface-50);
  border: 1px solid var(--surface-100);
}

/* Fade In animation */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>