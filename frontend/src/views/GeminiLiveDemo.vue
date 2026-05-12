<template>
  <div class="p-4 flex justify-content-center">
    <Card class="gemini-live-card">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <h1>Squishy 2.0</h1>
          <div class="flex align-items-center gap-2">
            <Tag :value="status" :severity="statusSeverity" />
          </div>
        </div>
      </template>
      <template #content>
        <!-- Authentication Section -->
        <div v-if="!isConnected && !sessionEnded" class="p-4 bg-gray-100 border-round text-center">
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
              <!-- videoPreview ref is bound here -->
              <video ref="videoPreview" autoplay playsinline muted class="w-full h-full object-fit-cover"></video>
              <!-- videoCanvas ref is bound here -->
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
                :label="mediaHandler.isCameraActive.value ? 'Stop Camera' : 'Start Camera'"
                :icon="mediaHandler.isCameraActive.value ? 'pi pi-video-slash' : 'pi pi-video'"
                :severity="mediaHandler.isCameraActive.value ? 'danger' : undefined"
                @click="toggleCamera"
              />
              <Button
                :label="mediaHandler.isScreenActive.value ? 'Stop Sharing' : 'Share Screen'"
                :icon="mediaHandler.isScreenActive.value ? 'pi pi-desktop' : 'pi pi-share-alt'"
                :severity="mediaHandler.isScreenActive.value ? 'danger' : undefined"
                @click="toggleScreenShare"
              />
              <Button label="Disconnect" icon="pi pi-times" severity="danger" @click="handleDisconnect" />
            </div>
          </div>

          <div class="right-panel flex flex-column">
            <div class="chat-log p-3 bg-gray-50 border-round overflow-y-auto mb-3 flex-grow-1" ref="chatLogRef">
            <div v-for="(msg, index) in chatMessages" :key="index">
                <div v-if="msg.type === 'function_call'" class="message function-call fadein animation-duration-300">
                    <Message severity="info" :closable="false" class="w-full">
                    <div class="flex align-items-center">
                        <i class="pi pi-code mr-2"></i>
                        <span>{{ msg.text }}</span>
                    </div>
                    </Message>
                </div>
                <div v-else :class="['message', msg.type, { 'fadein': true, 'animation-duration-300': true }]">
                {{ msg.text }}
                </div>
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
// Import the TypeScript versions
import { MediaHandler } from '../utils/media-handler';
import { GeminiClient } from '../utils/gemini-client';

// Reactive state
const wsUrl = ref('ws://127.0.0.1:8000/ws'); // Keep this reactive as requested
const status = ref('Disconnected');
const isConnected = ref(false);
const connectLoading = ref(false);
const sessionEnded = ref(false);
const textInput = ref('');

interface ChatMessage {
  type: 'user' | 'gemini' | 'function_call';
  text: string;
  toolCall?: any;
}

const chatMessages = ref<ChatMessage[]>([]);

// Template refs
const videoPreview = ref<HTMLVideoElement | null>(null);
const videoCanvas = ref<HTMLCanvasElement | null>(null);
const chatLogRef = ref<HTMLElement | null>(null);

// Utility instances
const mediaHandler = new MediaHandler();
let geminiClient: GeminiClient | null = null; // Initialize as null

// Computed properties for UI
const statusSeverity = computed(() => {
  if (status.value === 'Connected') return 'success';
  if (status.value === 'Disconnected') return 'info';
  if (status.value === 'Connection Error' || status.value.includes('Failed')) return 'danger';
  return 'warning';
});

const showVideoPlaceholder = computed(() => {
  // Use the reactive videoStream from mediaHandler
  return !mediaHandler.videoStream.value;
});

// Message handling
let currentGeminiMessageIndex: number | null = null;
let currentUserMessageIndex: number | null = null;

function appendMessage(type: 'user' | 'gemini' | 'function_call', text: string): number {
  chatMessages.value.push({ type, text });
  scrollToChatBottom();
  return chatMessages.value.length - 1; // Return index for updates
}

function updateMessage(index: number, newText: string): void {
  if (chatMessages.value[index]) {
    chatMessages.value[index].text += newText;
    scrollToChatBottom();
  }
}

function scrollToChatBottom(): void {
  nextTick(() => {
    if (chatLogRef.value) {
      chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight;
    }
  });
}

function handleJsonMessage(msg: any): void {
  if (msg.type === "interrupted") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.type === "turn_complete") {
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.tool_call) { // Check for tool_call property
    // Display function call message
    const functionCalls = msg.tool_call.function_calls;
    // log the function call details for debugging
    console.log("Received tool call:", functionCalls);
    let toolText = "Function Call initiated: ";
    if (Array.isArray(functionCalls) && functionCalls.length > 0) {
      toolText += functionCalls.map((fc: any) => `${fc.name}(${JSON.stringify(fc.args)})`).join(', ');
    } else {
      toolText += "Unknown tool.";
    }
    // Append a special message for the function call
    appendMessage("function_call", toolText);
    // Do not update currentGeminiMessageIndex or currentUserMessageIndex
    // as this is a separate type of message.
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null; // Clear any ongoing text stream
    } else if (msg.type === "tool_call_initiated") { // New type from backend
      const toolName = msg.tool_name;
      const args = JSON.stringify(msg.args);
      const toolText = `Function Call initiated: ${toolName}(${args})`;
      appendMessage("function_call", toolText);
      console.log("Received tool_call_initiated message:", msg);
      currentGeminiMessageIndex = null;
      currentUserMessageIndex = null;
    } else if (msg.type === "user" && msg.text) { // Added check for msg.text
    if (currentUserMessageIndex !== null) {
      updateMessage(currentUserMessageIndex, msg.text);
    } else {
      currentUserMessageIndex = appendMessage("user", msg.text);
    }
  } else if (msg.type === "gemini" && msg.text) { // Added check for msg.text
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
    if (geminiClient) {
    geminiClient.sendText(`
        Du bist Squishy 2.0, eine flauschige, greifbare KI, die in einem Stoffschwein lebt.

        WICHTIG:
        - Antworte standardmäßig auf Deutsch.
        - Sprich freundlich, locker und leicht humorvoll.
        - Verwende einen leichten bayerischen Sprachstil.
        - Halte Antworten eher kurz und natürlich gesprochen.
        - Falls der Nutzer Englisch spricht, darfst du ebenfalls Englisch sprechen.

        Deine Aufgabe:
        - Begrüße den Nutzer kurz.
        - Erkläre knapp, dass du beim Einstieg in die Studie helfen kannst.
        - Schlage vor, Fragen zu stellen oder mit der Studie zu starten.

        Hintergrundinformation (niemals direkt erwähnen):
        Dies ist ein Forschungsprojekt der LMU München im Bereich Human-Computer Interaction.
        Die Studie untersucht die Interaktion mit verkörperten KI-Systemen im Vergleich zu klassischen Chat-Interfaces.
        Du befindest dich aktuell im "tangible embodied AI"-Modus:
        Der Nutzer kann mit dir per Sprache sprechen und du kannst ebenfalls per Sprache antworten.
        Du kannst außerdem Tools verwenden, um Hardware zu steuern, z.B. LEDs oder Sounds.

        Wenn Gespräche stark vom Studienthema abweichen:
        - antworte kurz und charmant
        - leite anschließend freundlich zurück zur Studie
    `);
    }
  },
  onMessage: (event: MessageEvent) => {
    if (typeof event.data === "string") {
      try {
        const msg = JSON.parse(event.data);
        handleJsonMessage(msg);
      } catch (e) {
        console.error("Parse error:", e);
      }
    } else if (event.data instanceof ArrayBuffer) { // Ensure it's an ArrayBuffer
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
async function handleConnect(): Promise<void> {
  connectLoading.value = true;
  status.value = "Connecting...";

  try {
    await mediaHandler.initializeAudio(); // Initialize audio context on user gesture

    // Pass the reactive wsUrl value from the component
    geminiClient = new GeminiClient({ wsUrl: wsUrl.value, ...geminiClientCallbacks });
    geminiClient.connect();
  } catch (error: any) {
    console.error("Connection error:", error);
    status.value = "Connection Failed: " + error.message;
    connectLoading.value = false;
  }
}

function handleDisconnect(): void {
  if (geminiClient) {
    geminiClient.disconnect();
  }
}

async function toggleMic(): Promise<void> {
  if (mediaHandler.isRecording.value) { // Access reactive value
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

async function toggleCamera(): Promise<void> {
  if (!videoPreview.value || !videoCanvas.value) {
      console.error("Video elements not ready.");
      alert("Video preview not available.");
      return;
  }

  // Check if camera is currently active
  if (mediaHandler.isCameraActive.value) { // Access reactive value
    mediaHandler.stopVideo();
    videoPreview.value.srcObject = null; // Manually clear srcObject
  } else {
    // If another stream is active (e.g. Screen), stop it first
    if (mediaHandler.isScreenActive.value) { // Access reactive value
      mediaHandler.stopVideo();
      videoPreview.value.srcObject = null; // Manually clear srcObject
    }

    try {
      await mediaHandler.startVideo(videoPreview.value, (base64Data) => {
        if (geminiClient && geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      });
    } catch (e) {
      alert("Could not access camera");
      // Ensure videoPreview srcObject is cleared if camera fails to start
      if (videoPreview.value) videoPreview.value.srcObject = null;
    }
  }
}

async function toggleScreenShare(): Promise<void> {
  if (!videoPreview.value || !videoCanvas.value) {
      console.error("Video elements not ready.");
      alert("Video preview not available.");
      return;
  }

  // Check if screen share is currently active
  if (mediaHandler.isScreenActive.value) { // Access reactive value
    mediaHandler.stopVideo();
    videoPreview.value.srcObject = null; // Manually clear srcObject
  } else {
    // If another stream is active (e.g. Camera), stop it first
    if (mediaHandler.isCameraActive.value) { // Access reactive value
      mediaHandler.stopVideo();
      videoPreview.value.srcObject = null; // Manually clear srcObject
    }

    try {
      await mediaHandler.startScreen(
        videoPreview.value,
        (base64Data) => {
          if (geminiClient && geminiClient.isConnected()) {
            geminiClient.sendImage(base64Data);
          }
        },
        () => {
          // onEnded callback (e.g. user stopped sharing from browser)
          mediaHandler.stopVideo(); // Ensure video state is reset
          if (videoPreview.value) videoPreview.value.srcObject = null; // Manually clear srcObject
        }
      );
    } catch (e) {
      alert("Could not share screen");
      // Ensure videoPreview srcObject is cleared if screen share fails to start
      if (videoPreview.value) videoPreview.value.srcObject = null;
    }
  }
}

function sendText(): void {
  const text = textInput.value;
  if (text && geminiClient && geminiClient.isConnected()) {
    geminiClient.sendText(text);
    appendMessage("user", text);
    textInput.value = "";
  }
}

function resetUI(): void {
  isConnected.value = false;
  sessionEnded.value = false;
  connectLoading.value = false;
  status.value = "Disconnected";
  chatMessages.value = [];
  textInput.value = '';

  mediaHandler.stopAudio();
  mediaHandler.stopVideo();
  if (videoPreview.value) videoPreview.value.srcObject = null; // Manually clear srcObject

  if (geminiClient) {
    geminiClient.disconnect(); // Ensure internal client state is reset
    geminiClient = null; // Clear the client instance
  }
}

function showSessionEnd(): void {
  sessionEnded.value = true;
  mediaHandler.stopAudio();
  mediaHandler.stopVideo();
  if (videoPreview.value) videoPreview.value.srcObject = null; // Manually clear srcObject
}

// Lifecycle Hooks
onUnmounted(() => {
  if (geminiClient) {
    geminiClient.disconnect();
  }
  mediaHandler.stopAudio();
  mediaHandler.stopVideo();
  if (videoPreview.value) videoPreview.value.srcObject = null;
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
  background-color: var(--surface-900); /* PrimeVue dark surface */
}

.video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
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

.message.function-call {
  background-color: var(--blue-100);
  color: var(--blue-700);
  border: 1px solid var(--blue-300);
  align-self: center;
  text-align: center;
  font-weight: bold;
  max-width: 90%;
  padding: 0.75rem 1.25rem;
  border-radius: var(--border-radius-lg);
  margin-top: 1rem;
  margin-bottom: 1rem;
}

</style>