<!-- FILE: src/views/GeminiLiveScreen.vue -->

<template>
  <div class="p-4 flex justify-content-center">
    <div class="corner-actions">
      <Button
        icon="pi pi-shield"
        rounded
        text
        severity="secondary"
        aria-label="Open admin dashboard"
        @click="openAdminDashboard"
      />
      <!-- <Button
        icon="pi pi-bookmark"
        rounded
        text
        severity="secondary"
        aria-label="Open saved memories"
        @click="openMemoriesDialog"
      /> -->
      <Button
        icon="pi pi-cog"
        rounded
        text
        severity="secondary"
        aria-label="Open username settings"
        @click="usernameDialogVisible = true"
      />
    </div>

    <Dialog v-model:visible="usernameDialogVisible" modal header="Username" :style="{ width: '28rem' }">
      <div class="flex flex-column gap-3">
        <label for="session-username" class="font-medium">How would you like to be called?</label>
        <InputText id="session-username" v-model="username" placeholder="Dein Name" @keyup.enter="saveUsername" />

        <div class="flex flex-column gap-2">
          <label for="participant-id" class="font-medium">Participant-ID</label>
          <InputText id="participant-id" v-model="participantId" placeholder="Teilnehmer-ID" />
          <small class="text-color-secondary">Is used to determine the User and linked interactions</small>
        </div>

        <div class="flex flex-column gap-2 mt-2">
          <label class="font-medium">System Messages inline during Chat</label>
          <div class="flex align-items-center justify-content-between">
            <span class="text-sm text-color-secondary">System-Infos</span>
            <Checkbox v-model="messageVisibility.showSystemMessages" binary />
          </div>
          <div class="flex align-items-center justify-content-between">
            <span class="text-sm text-color-secondary">Tool Calls</span>
            <Checkbox v-model="messageVisibility.showToolCalls" binary />
          </div>
          <div class="flex align-items-center justify-content-between">
            <span class="text-sm text-color-secondary">Hardware-/Sensor-Input</span>
            <Checkbox v-model="messageVisibility.showHardwareInput" binary />
          </div>
        </div>

        <!-- <div class="flex flex-column gap-2 mt-2">
          <label class="font-medium">Routing-Steuerung</label>
          <div class="flex align-items-center justify-content-between">
            <span class="text-sm text-color-secondary">Hardware Mic (Input an KI)</span>
            <Checkbox v-model="routingConfig.hardwareMicEnabled" binary />
          </div>
          <div class="flex align-items-center justify-content-between">
            <span class="text-sm text-color-secondary">Hardware Speaker (Audio von KI)</span>
            <Checkbox v-model="routingConfig.hardwareSpeakerEnabled" binary />
          </div>
          <div class="flex align-items-center justify-content-between">
            <span class="text-sm text-color-secondary">UI Text Mode (Text Input in UI)</span>
            <Checkbox v-model="routingConfig.uiTextModeEnabled" binary />
          </div>
          <small class="text-color-secondary">Die Hardware darf weiter streamen, aber der Server kann Eingabe/Ausgabe gezielt ignorieren.</small>
        </div> -->

        <div class="flex flex-column gap-2 mt-2">
          <label for="gemini-api-key" class="font-medium">Gemini API Key (dynamic)</label>
          <InputText id="gemini-api-key" v-model="geminiApiKeyDraft" type="password" placeholder="Neuen API Key einfügen" />
          <small class="text-color-secondary">
            Sets the Gemini key without a server restart. After that, the active Gemini session is technically reinitialized.
          </small>
          <div class="flex gap-2 flex-wrap">
            <Button
              label="API Key anwenden"
              icon="pi pi-key"
              size="small"
              :loading="adminActionLoading"
              @click="applyGeminiApiKey"
            />
            <Button
              label="Fallback auf .env Key"
              icon="pi pi-undo"
              size="small"
              severity="secondary"
              outlined
              :loading="adminActionLoading"
              @click="fallbackGeminiApiKey"
            />
          </div>
        </div>

        <!-- <div class="flex flex-column gap-2 mt-2">
          <label class="font-medium">Recovery / Admin Aktionen</label>
          <small class="text-color-secondary">
            Nutze diese Buttons, wenn Gemini nicht mehr antwortet oder die Hardware neu gestartet werden soll.
          </small>
          <div class="flex gap-2 flex-wrap">
            <Button
              label="Force Restart Gemini Session"
              icon="pi pi-refresh"
              size="small"
              severity="warning"
              :loading="adminActionLoading"
              @click="forceRestartSession"
            />
            <Button
              label="Restart Hardware Client"
              icon="pi pi-power-off"
              size="small"
              severity="danger"
              outlined
              :loading="adminActionLoading"
              @click="restartHardwareClient"
            />
          </div>
          <Button
            label="Open Admin Dashboard"
            icon="pi pi-external-link"
            text
            size="small"
            class="justify-content-start p-0 mt-1"
            @click="openAdminDashboard"
          />
        </div> -->
        <div class="flex flex-column gap-2 mt-2">
          <label class="font-medium">Session Settings</label>
          <small class="text-color-secondary">
            Disconnect from the current session and stop the Interface.
          </small>
          <div class="flex gap-2 flex-wrap">
            <Button label="Disconnect" icon="pi pi-times" severity="danger" @click="handleDisconnect" />
          </div>
        </div>

        <small v-if="adminActionMessage" class="text-color-secondary">{{ adminActionMessage }}</small>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" text @click="usernameDialogVisible = false" />
        <Button label="Speichern" @click="saveUsername" />
      </template>
    </Dialog>

    <Dialog v-model:visible="memoriesDialogVisible" modal header="Gespeicherte Erinnerungen" :style="{ width: '42rem' }">
      <div class="memories-content">
        <div class="memories-toolbar">
          <Tag :value="`Teilnehmer: ${participantId}`" severity="secondary" />
          <Button label="Neu laden" icon="pi pi-refresh" text size="small" :loading="memoriesLoading" @click="loadMemories" />
        </div>
        <div v-if="memoriesError" class="memories-error">{{ memoriesError }}</div>
        <div v-else-if="memoriesLoading" class="memories-state">Loading Memories...</div>
        <div v-else-if="savedMemories.length === 0" class="memories-state">No Memorier found so far.</div>
        <div v-else class="memories-list">
          <div v-for="memory in savedMemories" :key="memory.id" class="memory-item">
            <div class="memory-meta">
              <Tag :value="memory.source || 'unknown'" severity="info" />
              <small>{{ formatMemoryDate(memory.created) }}</small>
            </div>
            <div class="memory-text">{{ memory.content }}</div>
          </div>
        </div>
      </div>
    </Dialog>

    <Card class="gemini-live-card">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <div class="flex align-items-center gap-2">
            <h1>Tangible AI Assistant</h1>
            <Tag :value="displayUsername" severity="info" icon="pi pi-user" />
          </div>
          <div class="flex align-items-center gap-2">
            <Tag :value="status" :severity="statusSeverity" />
            <Tag :value="hardwareStatusLabel" :severity="hardwareStatusSeverity" />
            <Tag v-if="clientIdShort" :value="`ID: ${clientIdShort}`" severity="secondary" />
            <Tag
              v-if="activeControllerId"
              :value="`Active: ${activeControllerType}`"
              :severity="isActiveController ? 'contrast' : 'info'"
              :icon="isActiveController ? 'pi pi-user-plus' : 'pi pi-user'"
            />
            <!-- <Button
              v-if="isConnected && !isActiveController"
              label="Take Control"
              icon="pi pi-user-plus"
              severity="secondary"
              size="small"
              @click="requestActiveController"
              aria-label="Request active controller role"
              v-tooltip.bottom="'Request to become the active controller for audio/text interaction.'"
            /> -->
          </div>
        </div>
      </template>
      <template #content>
        <div v-if="!isConnected && !sessionEnded" class="p-4 bg-gray-100 border-round text-center">
          <p class="mb-3">Click below to connect to your "Tangible AI Assistant" backend.</p>
          <Button label="Connect" icon="pi pi-bolt" :loading="connectLoading" @click="handleConnect" />
        </div>

        <div v-if="sessionEnded" class="p-5 bg-gray-50 border-round text-center fadein animation-duration-500">
          <h2 class="mt-0 mb-3">Session Ended</h2>
          <Button label="Start New Session" icon="pi pi-refresh" @click="resetUI" />
        </div>

        <div v-if="isConnected && !sessionEnded" class="conversation-shell">
          <!-- <div class="utility-actions">
            
          </div> -->

          <div v-if="false" class="legacy-video-panel hidden-legacy-controls">
            <div v-if="showVideoPlaceholder" class="legacy-video-placeholder">
              <span>No camera preview connected.</span>
            </div>
            <video ref="videoPreview" class="legacy-video-stream" muted playsinline />
            <canvas ref="videoCanvas" class="legacy-video-canvas" />
            <Button label="Toggle Camera" icon="pi pi-video" size="small" @click="toggleCamera" />
            <Button label="Toggle Screen" icon="pi pi-desktop" size="small" @click="toggleScreenShare" />
          </div>

          <div class="chat-log" ref="chatLogRef">
            <div v-for="(msg, index) in chatMessages" :key="index" :class="['message-row', msg.type]">
              <div v-if="msg.type === 'hardware' && msg.chipLabel" class="hardware-chip-standalone">
                <span class="hardware-chip" :style="{ borderColor: msg.chipColor || '#a855f7' }">
                  <span class="hardware-chip-dot" :style="{ backgroundColor: msg.chipColor || '#a855f7' }"></span>
                  {{ msg.chipLabel }}
                </span>
              </div>
              <div
                v-if="msg.type === 'system' || msg.type === 'error' || msg.type === 'function_call' || (msg.type === 'hardware' && !msg.chipLabel)"
                class="message-system"
                :class="msg.type"
              >
                <span class="badge">{{ msg.type === 'system' ? 'System' : msg.type === 'error' ? 'Error' : msg.type === 'hardware' ? 'Hardware' : 'Tool' }}</span>
                <div v-if="msg.text" class="message-content" v-html="renderMarkdown(msg.text)"></div>
              </div>
              <div v-else-if="msg.type === 'user' || msg.type === 'gemini'" class="message-bubble" :class="msg.type" v-html="renderMarkdown(msg.text)"></div>
            </div>
          </div>

          <div class="composer">
            <!-- <Button
              icon="pi pi-sliders-h"
              severity="secondary"
              text
              rounded
              aria-label="Open interaction simulations"
              @click="toggleGesturePopover"
            /> -->
            <Popover ref="gesturePopoverRef">
              <div class="gesture-grid popover-gesture-grid">
                <div v-for="gesture in gestureButtons" :key="gesture.code" class="gesture-card">
                  <Button
                    class="gesture-button"
                    :style="{
                      backgroundColor: gesture.color,
                      borderColor: gesture.color,
                      color: `color-mix(in srgb, ${gesture.color} 20%, #000000)`
                    }"
                    :icon="gesture.icon"
                    @click="sendGesture(gesture)"
                  >
                    <span class="gesture-button-content">
                      <span class="gesture-button-title">{{ gesture.name }}</span>
                    </span>
                  </Button>
                </div>
              </div>
            </Popover>
            <Button
              :label="mediaHandler.isRecording.value ? 'deactivate voice-mode' : 'activate voice-mode'"
              :icon="mediaHandler.isRecording.value ? 'pi pi-microphone-slash' : 'pi pi-microphone'"
              :severity="mediaHandler.isRecording.value ? 'danger' : 'secondary'"
              :disabled="!isActiveController && activeControllerId !== null"
              @click="toggleMic"
              v-tooltip.top="!isActiveController && activeControllerId !== null ? 'Only active controller can send mic input' : 'Aktiviert/Deaktiviert Sprachaufnahme über das Mikrofon.'"
            />
            <InputText
              v-model="textInput"
              placeholder="Type a message..."
              class="flex-grow"
              @keyup.enter="sendText"
              :disabled="(!isActiveController && activeControllerId !== null) || !routingConfig.uiTextModeEnabled"
              v-tooltip.top="!routingConfig.uiTextModeEnabled ? 'UI text mode is disabled.' : ((!isActiveController && activeControllerId !== null) ? 'Only active controller can send text input' : '')"
            />
            <Button
              label="Send"
              icon="pi pi-send"
              @click="sendText"
              :disabled="(!isActiveController && activeControllerId !== null) || !routingConfig.uiTextModeEnabled"
            />
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, computed, nextTick, watch } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Checkbox from 'primevue/checkbox';
import Tag from 'primevue/tag';
import Dialog from 'primevue/dialog';
import Popover from 'primevue/popover';
import MarkdownIt from 'markdown-it';
import markdownItKatex from 'markdown-it-katex';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import javascript from 'highlight.js/lib/languages/javascript';
import json from 'highlight.js/lib/languages/json';
import bash from 'highlight.js/lib/languages/bash';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';
import { useRouter } from 'vue-router';

import { MediaHandler } from '../utils/media-handler';
import { GeminiClient } from '../utils/gemini-client';

hljs.registerLanguage('python', python);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('json', json);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sh', bash);

const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true,
  highlight: (code, lang) => {
    const normalizedLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
    try {
      return hljs.highlight(code, { language: normalizedLang }).value;
    } catch {
      return hljs.highlightAuto(code).value;
    }
  }
});
markdownRenderer.use(markdownItKatex);

function renderMarkdown(text: string): string {
  return markdownRenderer.render(text || '');
}

function generateParticipantId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `participant-${Date.now()}`;
}

function ensureParticipantId(): string {
  const trimmed = participantId.value.trim();
  if (trimmed) {
    participantId.value = trimmed;
    return trimmed;
  }
  const generated = generateParticipantId();
  participantId.value = generated;
  localStorage.setItem(PARTICIPANT_ID_STORAGE_KEY, generated);
  return generated;
}

function getDefaultWsUrl(): string {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/ws';
  const secure = window.location.protocol === 'https:';
  const protocol = secure ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/ws`;
}

function getApiBaseUrl(): string {
  const ws = wsUrl.value.trim();
  if (ws.startsWith('/')) {
    return typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000';
  }
  if (ws.startsWith('wss://')) return ws.replace('wss://', 'https://').replace(/\/ws$/, '');
  if (ws.startsWith('ws://')) return ws.replace('ws://', 'http://').replace(/\/ws$/, '');
  if (typeof window !== 'undefined') return window.location.origin;
  return 'http://127.0.0.1:8000';
}

function applyHardwareStatus(statusPayload: any): void {
  const statusText = statusPayload?.status_text || 'Prototype not connected';
  hardwareStatusLabel.value = statusText;
  if (statusPayload?.connected) {
    hardwareStatusSeverity.value = 'success';
    return;
  }
  if (typeof statusPayload?.last_keepalive_age_seconds === 'number') {
    hardwareStatusSeverity.value = 'warning';
    return;
  }
  hardwareStatusSeverity.value = 'secondary';
}

async function refreshHardwareStatus(): Promise<void> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/admin/status`);
    if (!res.ok) {
      return;
    }
    const payload = await res.json();
    applyHardwareStatus(payload?.hardware_status);
  } catch {
    // ignore transient polling errors
  }
}

function startHardwareStatusPolling(): void {
  stopHardwareStatusPolling()
  void refreshHardwareStatus();
  hardwareStatusPollHandle = window.setInterval(() => {
    void refreshHardwareStatus();
  }, 3000);
}

function stopHardwareStatusPolling(): void {
  if (hardwareStatusPollHandle !== null) {
    window.clearInterval(hardwareStatusPollHandle);
    hardwareStatusPollHandle = null;
  }
}

function toggleGesturePopover(event: Event): void {
  gesturePopoverRef.value?.toggle(event);
}

function openAdminDashboard(): void {
  router.push('/admin-dashboard');
}

function formatMemoryDate(rawDate: string): string {
  const parsed = new Date(rawDate);
  if (Number.isNaN(parsed.getTime())) return rawDate;
  return parsed.toLocaleString();
}

// Reactive state
const wsUrl = ref(getDefaultWsUrl());
const status = ref('Disconnected');
const isConnected = ref(false);
const connectLoading = ref(false);
const sessionEnded = ref(false);
const textInput = ref('');
const PARTICIPANT_ID_STORAGE_KEY = 'squishy-participant-id';
const username = ref<string>(localStorage.getItem('squishy-username') || 'Guest');
const participantId = ref<string>(localStorage.getItem(PARTICIPANT_ID_STORAGE_KEY) || '');
const usernameDialogVisible = ref(false);
const memoriesDialogVisible = ref(false);
const memoriesLoading = ref(false);
const memoriesError = ref('');
const geminiApiKeyDraft = ref('');
const adminActionLoading = ref(false);
const adminActionMessage = ref('');
const hardwareStatusLabel = ref('Prototype not connected');
const hardwareStatusSeverity = ref<'success' | 'warning' | 'secondary'>('secondary');
let geminiClient: GeminiClient | null = null;
let hardwareStatusPollHandle: number | null = null;
const router = useRouter();

// Chat message interface updated for new types
interface ChatMessage {
  type: 'user' | 'gemini' | 'function_call' | 'system' | 'hardware' | 'error';
  text: string;
  chipLabel?: string;
  chipColor?: string;
}

interface SavedMemory {
  id: string;
  content: string;
  source?: string;
  created: string;
}

interface GestureButtonConfig {
  code: string;
  name: string;
  backendEvent:
    | 'press_head'
    | 'hush'
    | 'drop_on_table'
    | 'tap_head'
    | 'target_focus'
    | 'horizontal_turn'
    | 'shake'
    | 'squeeze';
  icon: string;
  severity: 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'danger' | 'contrast';
  color: string;
}

const VISIBILITY_STORAGE_KEY = 'squishy-message-visibility';
const ROUTING_STORAGE_KEY = 'squishy-routing-config';
const defaultMessageVisibility = {
  showSystemMessages: true,
  showToolCalls: true,
  showHardwareInput: true,
};
const defaultRoutingConfig = {
  hardwareMicEnabled: true,
  hardwareSpeakerEnabled: true,
  uiTextModeEnabled: true,
};

const messageVisibility = ref({ ...defaultMessageVisibility });
const routingConfig = ref({ ...defaultRoutingConfig });

function loadMessageVisibility() {
  try {
    const raw = localStorage.getItem(VISIBILITY_STORAGE_KEY);
    if (!raw) return { ...defaultMessageVisibility };
    const parsed = JSON.parse(raw);
    return {
      ...defaultMessageVisibility,
      ...parsed,
    };
  } catch {
    return { ...defaultMessageVisibility };
  }
}

function persistMessageVisibility() {
  localStorage.setItem(VISIBILITY_STORAGE_KEY, JSON.stringify(messageVisibility.value));
}

function loadRoutingConfig() {
  try {
    const raw = localStorage.getItem(ROUTING_STORAGE_KEY);
    if (!raw) return { ...defaultRoutingConfig };
    const parsed = JSON.parse(raw);
    return {
      ...defaultRoutingConfig,
      ...parsed,
    };
  } catch {
    return { ...defaultRoutingConfig };
  }
}

function persistRoutingConfig() {
  localStorage.setItem(ROUTING_STORAGE_KEY, JSON.stringify(routingConfig.value));
}

watch(
  messageVisibility,
  () => {
    persistMessageVisibility();
  },
  { deep: true }
);

watch(
  routingConfig,
  () => {
    persistRoutingConfig();
    if (geminiClient && geminiClient.isConnected()) {
      geminiClient.sendRoutingConfig({
        hardwareMicEnabled: routingConfig.value.hardwareMicEnabled,
        hardwareSpeakerEnabled: routingConfig.value.hardwareSpeakerEnabled,
        uiTextModeEnabled: routingConfig.value.uiTextModeEnabled,
      });
    }
  },
  { deep: true }
);

messageVisibility.value = loadMessageVisibility();
routingConfig.value = loadRoutingConfig();
ensureParticipantId();

const chatMessages = ref<ChatMessage[]>([]);
const savedMemories = ref<SavedMemory[]>([]);

const gestureButtons: GestureButtonConfig[] = [
  {
    code: 'R1_Activate',
    name: 'Activate the Assistant',
    backendEvent: 'press_head',
    icon: 'pi pi-power-off',
    severity: 'success',
    color: '#FFB3B3',
  },
  {
    code: 'R2_Stop',
    name: 'Stop the Assistant',
    backendEvent: 'hush',
    icon: 'pi pi-stop-circle',
    severity: 'danger',
    color: '#FFDBB3',
  },
  {
    code: 'R3_Concise',
    name: 'Be More Concise',
    backendEvent: 'drop_on_table',
    icon: 'pi pi-align-center',
    severity: 'info',
    color: '#FFFBB3',
  },
  {
    code: 'R4_Elaborate',
    name: 'Be More Elaborate',
    backendEvent: 'tap_head',
    icon: 'pi pi-file-edit',
    severity: 'primary',
    color: '#E3FFB3',
  },
  {
    code: 'R5_Save',
    name: 'Save Last Interaction',
    backendEvent: 'target_focus',
    icon: 'pi pi-bookmark',
    severity: 'warning',
    color: '#B3FFB3',
  },
  {
    code: 'R6_NewSession',
    name: 'Start New Session',
    backendEvent: 'horizontal_turn',
    icon: 'pi pi-refresh',
    severity: 'contrast',
    color: '#B3FFFB',
  },
  {
    code: 'R7_Options',
    name: 'Give Me Different Options',
    backendEvent: 'shake',
    icon: 'pi pi-directions-alt',
    severity: 'secondary',
    color: '#B3DBFF',
  },
  {
    code: 'R8_Optimize',
    name: 'Optimize Promt',
    backendEvent: 'squeeze',
    icon: 'pi pi-sliders-h',
    severity: 'info',
    color: '#B3B3FF',
  },
];

// Template refs
const videoPreview = ref<HTMLVideoElement | null>(null);
const videoCanvas = ref<HTMLCanvasElement | null>(null);
const chatLogRef = ref<HTMLElement | null>(null);
const gesturePopoverRef = ref<any>(null);

// Utility instances
const mediaHandler = new MediaHandler();

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

const displayUsername = computed(() => {
  return username.value.trim() || 'Guest';
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

function shouldDisplayMessage(type: ChatMessage['type']): boolean {
  if (type === 'function_call') return messageVisibility.value.showToolCalls;
  if (type === 'hardware') return messageVisibility.value.showHardwareInput;
  if (type === 'system') return messageVisibility.value.showSystemMessages;
  return true;
}

function appendMessage(type: ChatMessage['type'], text: string): number {
  if (!shouldDisplayMessage(type)) {
    return -1;
  }

  chatMessages.value.push({ type, text });
  scrollToChatBottom();
  return chatMessages.value.length - 1;
}

function appendHardwareMessage(text: string, chipLabel?: string, chipColor?: string): number {
  if (!shouldDisplayMessage('hardware')) {
    return -1;
  }
  chatMessages.value.push({ type: 'hardware', text, chipLabel, chipColor });
  scrollToChatBottom();
  return chatMessages.value.length - 1;
}

function getGestureConfigByEvent(eventName: string | undefined): GestureButtonConfig | undefined {
  if (!eventName) {
    return undefined;
  }
  return gestureButtons.find((gesture) => gesture.backendEvent === eventName);
}

function updateMessage(index: number, newText: string): void {
  if (index >= 0 && chatMessages.value[index]) {
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
    mediaHandler.stopAudio();
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
    appendMessage("system", msg.message);
  } else if (msg.type === "transcript") {
    currentGeminiMessageIndex = null;

    if (msg.is_final) {
        if (currentUserMessageIndex !== null) {
            updateMessage(currentUserMessageIndex, msg.text);
        } else {
            appendMessage("user", msg.text);
        }
        currentUserMessageIndex = null;
    } else {
        if (currentUserMessageIndex !== null) {
            updateMessage(currentUserMessageIndex, msg.text);
        } else {
            currentUserMessageIndex = appendMessage("user", msg.text);
        }
    }
  } else if (msg.type === "ai_response") {
    if (currentGeminiMessageIndex !== null) {
      updateMessage(currentGeminiMessageIndex, msg.text);
    } else {
      currentGeminiMessageIndex = appendMessage("gemini", msg.text);
    }
  } else if (msg.type === "tool_call") {
    const toolName = msg.tool_name;
    const args = JSON.stringify(msg.args);
    const suggestedAction = msg.suggested_action;
    const toolText = `Tool Call: ${toolName}(${args}) [${suggestedAction}]`;
    appendMessage("function_call", toolText);
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.type === "active_controller_change") {
    appendMessage("system", `Active controller changed to ${msg.new_active_controller_type} (ID: ${msg.new_active_controller_id.substring(0, 8)}).`);
  } else if (msg.type === "registration_ack" && msg.routing_config) {
    routingConfig.value = {
      hardwareMicEnabled: msg.routing_config.hardware_mic_enabled !== false,
      hardwareSpeakerEnabled: msg.routing_config.hardware_speaker_enabled !== false,
      uiTextModeEnabled: msg.routing_config.ui_text_mode_enabled !== false,
    };
  } else if (msg.type === "session_reset") {
    mediaHandler.stopAudioPlayback();
    mediaHandler.stopAudio();
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
    chatMessages.value = [];
  } else if (msg.type === "turn_complete") {
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
  } else if (msg.type === "sensor_event_observed") {
    const gestureEventName = msg.mapped_gesture || msg.event;
    const gestureConfig = getGestureConfigByEvent(gestureEventName);
    if (gestureConfig) {
      appendHardwareMessage('', gestureConfig.name, gestureConfig.color);
    }
  } else if (msg.type === "system_command") {
    const command = msg.command || msg.action;
    if (command === "set_microphone_state") {
      const enabled = Boolean(msg.payload?.enabled);
      void setMicrophoneEnabled(enabled);
      appendMessage("system", enabled ? "Mic activated by gesture." : "Mic deactivated by gesture.");
    }
  } else if (msg.type === "system_message") {
    appendMessage("system", msg.message);
  } else if (msg.type === "error") {
    appendMessage("error", msg.message);
  }
}
function saveUsername(): void {
  const trimmed = username.value.trim();
  const participant = ensureParticipantId();
  username.value = trimmed || 'Guest';
  localStorage.setItem('squishy-username', username.value);
  localStorage.setItem(PARTICIPANT_ID_STORAGE_KEY, participant);
  persistMessageVisibility();
  persistRoutingConfig();
  if (geminiClient && geminiClient.isConnected()) {
    geminiClient.sendRoutingConfig({
      hardwareMicEnabled: routingConfig.value.hardwareMicEnabled,
      hardwareSpeakerEnabled: routingConfig.value.hardwareSpeakerEnabled,
      uiTextModeEnabled: routingConfig.value.uiTextModeEnabled,
    });
  }
  usernameDialogVisible.value = false;
}

async function loadMemories(): Promise<void> {
  memoriesLoading.value = true;
  memoriesError.value = '';
  try {
    const participant = ensureParticipantId();
    const url = `${getApiBaseUrl()}/api/memories?participant_id=${encodeURIComponent(participant)}`;
    const response = await fetch(url);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }
    const payload = await response.json();
    savedMemories.value = Array.isArray(payload.items) ? payload.items : [];
  } catch (error: any) {
    memoriesError.value = `Konnte Erinnerungen nicht laden: ${error.message ?? String(error)}`;
  } finally {
    memoriesLoading.value = false;
  }
}

async function openMemoriesDialog(): Promise<void> {
  memoriesDialogVisible.value = true;
  await loadMemories();
}

async function runAdminAction<T>(action: () => Promise<T>, successMessage: string): Promise<T | null> {
  adminActionLoading.value = true;
  adminActionMessage.value = '';
  try {
    const result = await action();
    adminActionMessage.value = successMessage;
    return result;
  } catch (error: any) {
    const message = error?.message ?? String(error);
    adminActionMessage.value = `Fehler: ${message}`;
    appendMessage('error', adminActionMessage.value);
    return null;
  } finally {
    adminActionLoading.value = false;
  }
}

async function applyGeminiApiKey(): Promise<void> {
  const key = geminiApiKeyDraft.value.trim();
  if (!key) {
    adminActionMessage.value = 'Bitte zuerst einen API Key einfügen oder den Fallback-Button nutzen.';
    return;
  }

  const response = await runAdminAction(
    async () => {
      const res = await fetch(`${getApiBaseUrl()}/api/admin/gemini-api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key, use_fallback: true }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      return res.json();
    },
    'Gemini API Key aktualisiert. Session wurde neu initialisiert.'
  );

  if (response) {
    geminiApiKeyDraft.value = '';
    appendMessage('system', 'Gemini API key updated via admin settings.');
  }
}

async function fallbackGeminiApiKey(): Promise<void> {
  const response = await runAdminAction(
    async () => {
      const res = await fetch(`${getApiBaseUrl()}/api/admin/gemini-api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: '', use_fallback: true }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      return res.json();
    },
    'Fallback auf .env Gemini API Key aktiviert.'
  );

  if (response) {
    appendMessage('system', 'Gemini API key fallback to default applied.');
  }
}

async function forceRestartSession(): Promise<void> {
  await runAdminAction(
    async () => {
      const res = await fetch(`${getApiBaseUrl()}/api/admin/session/restart`, {
        method: 'POST',
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      return res.json();
    },
    'Gemini Session wurde neu gestartet.'
  );
}

async function restartHardwareClient(): Promise<void> {
  const response = await runAdminAction(
    async () => {
      const res = await fetch(`${getApiBaseUrl()}/api/admin/hardware/restart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'restart' }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      return res.json();
    },
    'Restart-Befehl an Hardware-Clients gesendet.'
  );
  if (response && typeof response.sent_to_clients === 'number') {
    appendMessage('system', `Hardware restart command sent to ${response.sent_to_clients} client(s).`);
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
    if (geminiClient) {
      geminiClient.sendRoutingConfig({
        hardwareMicEnabled: routingConfig.value.hardwareMicEnabled,
        hardwareSpeakerEnabled: routingConfig.value.hardwareSpeakerEnabled,
        uiTextModeEnabled: routingConfig.value.uiTextModeEnabled,
      });
    }
    startHardwareStatusPolling();
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
    stopHardwareStatusPolling();
    applyHardwareStatus(undefined);
    showSessionEnd();
  },
  onError: (e: Event) => {
    console.error("WS Error:", e);
    status.value = "Connection Error";
    isConnected.value = false;
    stopHardwareStatusPolling();
  },
};

// UI Control Handlers
async function handleConnect(): Promise<void> {
const trimmedUsername = username.value.trim();
if (!trimmedUsername) {
  usernameDialogVisible.value = true;
  status.value = 'Username required';
  return;
}

username.value = trimmedUsername;
localStorage.setItem('squishy-username', trimmedUsername);
const participant = ensureParticipantId();
localStorage.setItem(PARTICIPANT_ID_STORAGE_KEY, participant);
connectLoading.value = true;
status.value = "Connecting...";

try {
  await mediaHandler.initializeAudio();

  geminiClient = new GeminiClient({
    wsUrl: wsUrl.value,
    username: trimmedUsername,
    participantId: participant,
    ...geminiClientCallbacks,
  });
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

async function startMicrophoneCapture(): Promise<void> {
  await mediaHandler.startAudio((data) => {
    if (geminiClient && geminiClient.isConnected()) {
      try {
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
}

async function setMicrophoneEnabled(enabled: boolean): Promise<void> {
  if (enabled) {
    if (mediaHandler.isRecording.value) {
      return;
    }
    try {
      await startMicrophoneCapture();
    } catch (e) {
      const details = String(e);
      const hint = typeof navigator !== 'undefined' && (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia)
        ? 'Microphone access needs a secure context (HTTPS) on remote devices.'
        : '';
      alert(`Could not start audio capture: ${details}${hint ? `\n${hint}` : ''}`);
    }
    return;
  }

  if (mediaHandler.isRecording.value) {
    mediaHandler.stopAudio();
  }
}

async function toggleMic(): Promise<void> {
  if (!isActiveController.value && activeControllerId.value !== null) {
    alert("You are not the active controller. Cannot send mic input.");
    return;
  }
  await setMicrophoneEnabled(!mediaHandler.isRecording.value);
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
      textInput.value = "";
      return;
  }
  if (text && geminiClient && geminiClient.isConnected()) {
    if (!routingConfig.value.uiTextModeEnabled) {
      appendMessage("system", "UI text mode is disabled. Text input was not sent.");
      textInput.value = "";
      return;
    }
    currentGeminiMessageIndex = null;
    currentUserMessageIndex = null;
    geminiClient.sendText(text);
    void setMicrophoneEnabled(false);
    appendMessage("user", text);
    textInput.value = "";
  }
}

function sendGesture(gesture: GestureButtonConfig): void {
  if (geminiClient && geminiClient.isConnected()) {
    geminiClient.sendGestureEvent(gesture.backendEvent);
    gesturePopoverRef.value?.hide();
  } else {
    alert('Not connected to send gesture events.');
  }
}

function resetUI(): void {
  isConnected.value = false;
  sessionEnded.value = false;
  connectLoading.value = false;
  status.value = "Disconnected";
  stopHardwareStatusPolling();
  applyHardwareStatus(undefined);
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
  stopHardwareStatusPolling();
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
.corner-actions {
position: absolute;
top: 1rem;
right: 1rem;
z-index: 10;
display: flex;
gap: 0.35rem;
}

.gemini-live-card {
max-width: 1200px;
width: 100%;
}

.p-card .p-card-content {
  padding-top: 0;
}

.conversation-shell {
display: flex;
flex-direction: column;
gap: 1rem;
}

.utility-actions,
.composer {
display: flex;
flex-wrap: wrap;
gap: 0.75rem;
align-items: center;
}

.gesture-grid {
display: grid;
grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
gap: 0.75rem;
width: 100%;
}

.popover-gesture-grid {
min-width: min(90vw, 360px);
}

.gesture-card {
display: flex;
flex-direction: column;
gap: 0.35rem;
}

.gesture-button {
width: 100%;
justify-content: flex-start;
text-align: left;
}

.gesture-button-content {
display: flex;
flex-direction: column;
align-items: flex-start;
gap: 0.1rem;
}

.gesture-button-title {
font-weight: 700;
}

.gesture-button-subtitle {
font-size: 0.82rem;
opacity: 0.92;
}

.gesture-caption {
color: var(--text-color-secondary);
padding-inline: 0.2rem;
word-break: break-word;
}

.memories-content {
display: flex;
flex-direction: column;
gap: 0.75rem;
}

.memories-toolbar {
display: flex;
align-items: center;
justify-content: space-between;
gap: 0.75rem;
}

.memories-state,
.memories-error {
padding: 0.6rem 0.2rem;
color: var(--text-color-secondary);
}

.memories-error {
color: #b91c1c;
}

.memories-list {
max-height: 55vh;
overflow-y: auto;
display: flex;
flex-direction: column;
gap: 0.65rem;
padding-right: 0.2rem;
}

.memory-item {
border: 1px solid var(--surface-200);
border-radius: 0.75rem;
padding: 0.65rem 0.8rem;
background: rgba(148, 163, 184, 0.06);
}

.memory-meta {
display: flex;
align-items: center;
justify-content: space-between;
gap: 0.75rem;
margin-bottom: 0.35rem;
}

.memory-text {
white-space: pre-wrap;
line-height: 1.5;
}

.chat-log {
min-height: 360px;
max-height: 70vh;
border: 1px solid var(--surface-200);
border-radius: 1rem;
background: linear-gradient(180deg, rgba(15, 23, 42, 0.02), rgba(15, 23, 42, 0.05));
padding: 1rem;
overflow-y: auto;
display: flex;
flex-direction: column;
gap: 0.9rem;
}

.message-row {
display: flex;
width: 100%;
}

.message-row.user {
justify-content: flex-end;
}

.message-row.gemini {
justify-content: flex-start;
}

.message-row.system,
.message-row.error,
.message-row.function_call,
.message-row.hardware {
justify-content: center;
}

.message-bubble,
.message-system {
max-width: min(78%, 820px);
border-radius: 1.1rem;
padding: 0.8rem 1rem;
line-height: 1.6;
word-break: break-word;
box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}

.message-row.user .message-bubble {
background: linear-gradient(135deg, #2563eb, #1d4ed8);
color: white;
border-bottom-right-radius: 0.45rem;
}

.message-row.gemini .message-bubble {
text-align: left !important;
background: rgba(255, 255, 255, 0.9);
border: 1px solid rgba(148, 163, 184, 0.25);
color: var(--text-color);
border-bottom-left-radius: 0.45rem;
}

.message-system {
width: min(75%, 620px);
border-radius: 0.85rem;
background: rgba(148, 163, 184, 0.08);
border: 1px solid rgba(148, 163, 184, 0.2);
color: var(--text-color);
font-size: 0.7rem;
padding: 0.45rem 0.65rem;
}

.message-system.error {
background: rgba(239, 68, 68, 0.08);
border-color: rgba(239, 68, 68, 0.2);
}

.message-system.function_call {
background: rgba(59, 130, 246, 0.08);
border-color: rgba(59, 130, 246, 0.2);
}

.message-system.hardware {
background: rgba(168, 85, 247, 0.06);
border-color: rgba(168, 85, 247, 0.2);
}

.hardware-chip-standalone {
display: inline-flex;
align-items: center;
justify-content: center;
width: 100%;
}

.hardware-chip {
display: inline-flex;
align-items: center;
gap: 0.35rem;
border: 1px solid;
border-radius: 999px;
padding: 0.1rem 0.45rem;
font-size: 0.65rem;
font-weight: 600;
margin-bottom: 0.45rem;
background: rgba(255, 255, 255, 0.7);
}

.hardware-chip-dot {
width: 0.45rem;
height: 0.45rem;
border-radius: 999px;
display: inline-block;
}

.badge {
display: inline-flex;
align-items: center;
border-radius: 999px;
padding: 0.15rem 0.5rem;
font-size: 0.58rem;
font-weight: 600;
letter-spacing: 0.04em;
text-transform: uppercase;
background: rgba(15, 23, 42, 0.06);
color: var(--text-color-secondary);
margin-bottom: 0.45rem;
}

.message-content {
display: block;
}

.message-bubble :deep(p),
.message-content :deep(p) {
margin: 0 0 0.5rem;
}

.message-bubble :deep(p:last-child),
.message-content :deep(p:last-child) {
margin-bottom: 0;
}

.message-bubble :deep(pre),
.message-content :deep(pre) {
margin: 0.7rem 0;
border-radius: 0.8rem;
overflow-x: auto;
padding: 0.9rem 1rem;
background: #0f172a;
color: #e2e8f0;
border: 1px solid rgba(148, 163, 184, 0.2);
}

.message-bubble :deep(code),
.message-content :deep(code) {
font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
font-size: 0.9em;
}

.message-bubble :deep(pre code),
.message-content :deep(pre code) {
padding: 0;
background: transparent;
border: none;
}

.message-bubble :deep(blockquote),
.message-content :deep(blockquote) {
border-left: 3px solid rgba(148, 163, 184, 0.5);
padding-left: 0.8rem;
margin: 0.75rem 0;
color: var(--text-color-secondary);
}

.message-bubble :deep(ul),
.message-bubble :deep(ol),
.message-content :deep(ul),
.message-content :deep(ol) {
margin: 0.5rem 0 0.5rem 1.25rem;
padding-left: 0.2rem;
}

.message-bubble :deep(table),
.message-content :deep(table) {
width: 100%;
border-collapse: collapse;
margin: 0.75rem 0;
}

.message-bubble :deep(th),
.message-bubble :deep(td),
.message-content :deep(th),
.message-content :deep(td) {
border: 1px solid rgba(148, 163, 184, 0.28);
padding: 0.4rem 0.6rem;
}

.message-bubble :deep(a),
.message-content :deep(a) {
color: inherit;
text-decoration: underline;
}

.message-bubble :deep(.katex),
.message-content :deep(.katex) {
font-size: 1.02em;
}

.composer {
border: 1px solid var(--surface-200);
border-radius: 1rem;
padding: 0.75rem;
background: rgba(255, 255, 255, 0.5);
}

.composer .p-inputtext {
flex: 1;
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