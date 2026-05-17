<!-- FILE: src/views/GeminiLiveScreen.vue -->

<template>
  <div class="p-4 flex justify-content-center">
    <Card class="gemini-live-card">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <h1>Squishy 2.0</h1>
          <div class="flex align-items-center gap-2">
            <Tag :value="status" :severity="statusSeverity" />
            <Tag v-if="clientIdShort" :value="`ID: ${clientIdShort}`" severity="secondary" />
            <Tag
              v-if="activeControllerId"
              :value="`Active: ${activeControllerType}`"
              :severity="isActiveController ? 'contrast' : 'info'"
              :icon="isActiveController ? 'pi pi-user-plus' : 'pi pi-user'"
            />
            <Button
              v-if="isConnected && !isActiveController"
              label="Take Control"
              icon="pi pi-user-plus"
              severity="secondary"
              size="small"
              @click="requestActiveController"
              aria-label="Request active controller role"
              v-tooltip.bottom="'Request to become the active controller for audio/text interaction.'"
            />
          </div>
        </div>
      </template>
      <template #content>
        <!-- Authentication Section -->
        <div v-if="!isConnected && !sessionEnded" class="p-4 bg-gray-100 border-round text-center">
          <p class="mb-3">Click below to connect to the unified Squishy backend.</p>
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
                :disabled="!isActiveController && activeControllerId !== null"
                @click="toggleMic"
                v-tooltip.bottom="!isActiveController && activeControllerId !== null ? 'Only active controller can send mic input' : ''"
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

            <Divider align="center">
              <span class="p-tag">Simulate Sensors</span>
            </Divider>
            <div class="flex flex-wrap gap-2 mb-3">
                <Button
                    label="Pet Gentle"
                    icon="pi pi-hand"
                    severity="success"
                    size="small"
                    @click="sendSimulatedSensor('touch_sensor_1', 'petted', 1, 'gentle')"
                    aria-label="Simulate gentle petting"
                />
                <Button
                    label="Pet Hard"
                    icon="pi pi-hand"
                    severity="warning"
                    size="small"
                    @click="sendSimulatedSensor('touch_sensor_1', 'petted', 3, 'hard')"
                    aria-label="Simulate hard petting"
                />
                <Button
                    label="Tilt Left"
                    icon="pi pi-angle-left"
                    severity="info"
                    size="small"
                    @click="sendSimulatedSensor('imu_sensor', 'tilted', 'left')"
                    aria-label="Simulate tilt left"
                />
                <Button
                    label="Button Press"
                    icon="pi pi-plus"
                    severity="secondary"
                    size="small"
                    @click="sendSimulatedSensor('button_sensor_a', 'pressed', 'single')"
                    aria-label="Simulate button press"
                />
            </div>

          </div>

          <div class="right-panel flex flex-column">
            <div class="chat-log p-3 bg-gray-50 border-round overflow-y-auto mb-3 flex-grow-1" ref="chatLogRef">
              <div v-for="(msg, index) in chatMessages" :key="index">
                <Message v-if="msg.type === 'system'" severity="secondary" :closable="false" class="w-full my-1">
                  <div class="flex align-items-center">
                      <i class="pi pi-info-circle mr-2"></i>
                      <span class="text-sm text-color-secondary">{{ msg.text }}</span>
                  </div>
                </Message>
                <Message v-else-if="msg.type === 'error'" severity="danger" :closable="false" class="w-full my-1">
                  <div class="flex align-items-center">
                      <i class="pi pi-exclamation-triangle mr-2"></i>
                      <span>{{ msg.text }}</span>
                  </div>
                </Message>
                <Message v-else-if="msg.type === 'function_call'" severity="info" :closable="false" class="w-full my-1">
                  <div class="flex align-items-center">
                      <i class="pi pi-code mr-2"></i>
                      <span>{{ msg.text }}</span>
                  </div>
                </Message>
                <div v-else :class="['message', msg.type, { 'fadein': true, 'animation-duration-300': true }]">
                  {{ msg.text }}
                </div>
              </div>
            </div>
            <div class="flex gap-2">
              <InputText
                v-model="textInput"
                placeholder="Type a message..."
                class="flex-grow"
                @keyup.enter="sendText"
                :disabled="!isActiveController && activeControllerId !== null"
                v-tooltip.top="!isActiveController && activeControllerId !== null ? 'Only active controller can send text input' : ''"
              />
              <Button
                label="Send"
                icon="pi pi-send"
                @click="sendText"
                :disabled="!isActiveController && activeControllerId !== null"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import Divider from 'primevue/divider';
import Tooltip from 'primevue/tooltip'; // Import Tooltip

// Register Tooltip globally if not already done in main.ts
// app.directive('tooltip', Tooltip);

import { MediaHandler } from '../utils/media-handler';
import { GeminiClient } from '../utils/gemini-client';

// Reactive state
const wsUrl = ref('ws://127.0.0.1:8000/ws');
const status = ref('Disconnected');
const isConnected = ref(false);
const connectLoading = ref(false);
const sessionEnded = ref(false);
const textInput = ref('');

// Chat message interface updated for new types
interface ChatMessage {
  type: 'user' | 'gemini' | 'function_call' | 'system' | 'error';
  text: string;
}

const chatMessages = ref<ChatMessage[]>([]);

// Template refs
const videoPreview = ref<HTMLVideoElement | null>(null);
const videoCanvas = ref<HTMLCanvasElement | null>(null);
const chatLogRef = ref<HTMLElement | null>(null);

// Utility instances
const mediaHandler = new MediaHandler();
let geminiClient: GeminiClient | null = null;

// Computed properties for UI
const statusSeverity = computed(() => {
  if (status.value === 'Connected') return 'success';
  if (status.value === 'Disconnected') return 'info';
  if (status.value === 'Connection Error' || status.value.includes('Failed')) return 'danger';
  return 'warning';
});

const showVideoPlaceholder = computed(() => {
  return !mediaHandler.videoStream.value;
});

const clientIdShort = computed(() => {
  return geminiClient?.clientId!.substring(0, 8) ?? '';
});

const activeControllerId = computed<string | null>(() => {
  return (geminiClient as any)?.activeControllerId?.value ?? null;
});

const activeControllerType = computed<string>(() => {
  return (geminiClient as any)?.activeControllerType?.value ?? '';
});

const isActiveController = computed(() => {
  return geminiClient?.clientId?.substring(0, 8) === activeControllerId.value?.substring(0, 8);
});

// Message handling
let currentGeminiMessageIndex: number | null = null;
let currentUserMessageIndex: number | null = null; // Backend might send user transcripts back

function appendMessage(type: ChatMessage['type'], text: string): number {
  chatMessages.value.push({ type, text });
  scrollToChatBottom();
  return chatMessages.value.length - 1;
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
  if (msg.type === "audio_interrupt") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
    appendMessage("system", msg.message);
  } else if (msg.type === "transcript") {
    // Transcripts can be for user or AI, based on context.
    // The backend only sends `transcript` from what it receives (user input).
    // So, we treat this as the user's recognized speech.
    if (msg.is_final) {
        if (currentUserMessageIndex !== null) {
            updateMessage(currentUserMessageIndex, msg.text); // Finalize the current user message
        } else {
            appendMessage("user", msg.text); // Or add a new one if it's a direct transcript
        }
        currentUserMessageIndex = null; // Reset for next user input
    } else {
        if (currentUserMessageIndex !== null) {
            updateMessage(currentUserMessageIndex, msg.text);
        } else {
            currentUserMessageIndex = appendMessage("user", msg.text); // Interim transcript
        }
    }
  } else if (msg.type === "ai_response") { // Gemini's actual text response
    if (currentGeminiMessageIndex !== null) {
      updateMessage(currentGeminiMessageIndex, msg.text);
    } else {
      currentGeminiMessageIndex = appendMessage("gemini", msg.text);
    }
  } else if (msg.type === "tool_call") {
    // This is the direct tool_call event from the backend
    const toolName = msg.tool_name;
    const args = JSON.stringify(msg.args);
    const suggestedAction = msg.suggested_action;
    let toolText = `Tool Call: ${toolName}(${args}) [${suggestedAction}]`;
    appendMessage("function_call", toolText);
    console.log("Received tool_call message:", msg);
    // You could add logic here to visually simulate the tool call in the UI
    // e.g., if (toolName === 'set_led_color') { updateLedVisual(args.color); }
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.type === "active_controller_change") {
    appendMessage("system", `Active controller changed to ${msg.new_active_controller_type} (ID: ${msg.new_active_controller_id.substring(0, 8)}).`);
    geminiClient?.sendText(`Stell dich selbst kurz vor und begrüße den Nutzer`);  
} else if (msg.type === "system_message") {
    appendMessage("system", msg.message);
  } else if (msg.type === "error") {
    appendMessage("error", msg.message);
  }
}

// WebSocket Callbacks for GeminiClient
const geminiClientCallbacks = {
  onOpen: () => {
    status.value = "Connected";
    isConnected.value = true;
    sessionEnded.value = false;
    connectLoading.value = false;

    // Send a system message to Gemini to set the persona
    if (geminiClient && isActiveController.value) { // Only send if frontend is active controller
        // wird aktuell nicht aufgerufen
    } else if (geminiClient && !isActiveController.value) {
      appendMessage("system", "Connected as observer. Waiting for active controller to initialize AI persona.");
    }
  },
  // *** REPARIERTER onMessage CALLBACK ***
  // It now receives either a parsed JSON object or a raw ArrayBuffer
  onMessage: (data: any) => { // Use 'any' for data initially as it can be object or ArrayBuffer
    if (data instanceof ArrayBuffer) {
      // This is raw audio data
      mediaHandler.playAudio(data);
    } else if (typeof data === "object" && data !== null) {
      // This is a parsed JSON object
      handleJsonMessage(data); // Pass the already parsed object
    } else {
      console.warn("Received unexpected message data type:", typeof data, data);
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
    await mediaHandler.initializeAudio();

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
  if (!isActiveController.value && activeControllerId.value !== null) {
      alert("You are not the active controller. Cannot send mic input.");
      return;
  }
  if (mediaHandler.isRecording.value) {
    mediaHandler.stopAudio();
  } else {
    try {
      await mediaHandler.startAudio((data) => {
        if (geminiClient && geminiClient.isConnected()) {
          try {
            // Ensure we pass a real ArrayBuffer (not a SharedArrayBuffer) to match GeminiClient.send signature
            let bufferToSend: ArrayBuffer;
            const srcView = new Uint8Array(data as ArrayBufferLike);
            const copy = new Uint8Array(srcView.length);
            copy.set(srcView);
            bufferToSend = copy.buffer;
            geminiClient.send(bufferToSend);
          } catch (err) {
            console.error('Failed to prepare audio buffer for sending', err);
          }
        }
      });
    } catch (e) {
      alert("Could not start audio capture: " + e);
    }
  }
}

async function toggleCamera(): Promise<void> {
  if (!videoPreview.value || !videoCanvas.value) {
      console.error("Video elements not ready.");
      alert("Video preview not available.");
      return;
  }

  if (mediaHandler.isCameraActive.value) {
    mediaHandler.stopVideo();
    videoPreview.value.srcObject = null;
  } else {
    if (mediaHandler.isScreenActive.value) {
      mediaHandler.stopVideo();
      videoPreview.value.srcObject = null;
    }

    try {
      await mediaHandler.startVideo(videoPreview.value, (base64Data) => {
        if (geminiClient && geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      });
    } catch (e) {
      alert("Could not access camera: " + e);
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

  if (mediaHandler.isScreenActive.value) {
    mediaHandler.stopVideo();
    videoPreview.value.srcObject = null;
  } else {
    if (mediaHandler.isCameraActive.value) {
      mediaHandler.stopVideo();
      videoPreview.value.srcObject = null;
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
          mediaHandler.stopVideo();
          if (videoPreview.value) videoPreview.value.srcObject = null;
        }
      );
    } catch (e) {
      alert("Could not share screen: " + e);
      if (videoPreview.value) videoPreview.value.srcObject = null;
    }
  }
}

function sendText(): void {
  const text = textInput.value;
  if (!isActiveController.value && activeControllerId.value !== null) {
      alert("You are not the active controller. Cannot send text input.");
      textInput.value = ""; // Clear input
      return;
  }
  if (text && geminiClient && geminiClient.isConnected()) {
    geminiClient.sendText(text);
    appendMessage("user", text); // Only append if actually sent
    textInput.value = "";
  }
}

function sendSimulatedSensor(sensorId: string, eventType: string, value: any, intensity?: string): void {
  if (geminiClient && geminiClient.isConnected()) {
      geminiClient.sendSensorEvent(sensorId, eventType, value, intensity);
      appendMessage("system", `Simulated sensor event: ${sensorId} - ${eventType} (Value: ${value})`);
  } else {
      alert("Not connected to send sensor events.");
  }
}

function requestActiveController(): void {
    if (geminiClient && geminiClient.isConnected() && geminiClient.clientId) {
        geminiClient.requestSetActiveController();
        appendMessage("system", "Requesting to become active controller...");
    } else {
        alert("Not connected or client ID not set. Cannot request active controller.");
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
  if (videoPreview.value) videoPreview.value.srcObject = null;

  if (geminiClient) {
    geminiClient.disconnect();
    geminiClient = null;
  }
}

function showSessionEnd(): void {
  sessionEnded.value = true;
  mediaHandler.stopAudio();
  mediaHandler.stopVideo();
  if (videoPreview.value) videoPreview.value.srcObject = null;
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
  max-height: 70vh; /* Limit height and allow scrolling */
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

/* Message component styling */
.p-message.p-component.w-full {
  margin-bottom: 0.5rem; /* Adjust spacing for message components */
}

</style>