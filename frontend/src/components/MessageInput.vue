// src/components/MessageInput.vue
<script setup lang="ts">
import { ref, computed } from "vue";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import MetadataSelector from "./MetadataSelector.vue";
import type { MessageMetadata, MessagePayload } from "../types";

const emit = defineEmits(["send"]);

const currentInput = ref<string>("");
const audioFileInput = ref<HTMLInputElement | null>(null);
const imageFileInput = ref<HTMLInputElement | null>(null);
const selectedMetadata = ref<MessageMetadata>({});

const props = defineProps<{
  disabled: boolean;
}>();

const isRecording = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const audioChunks = ref<Blob[]>([]);
const recordingTimer = ref<number>(0);
let timerInterval: ReturnType<typeof setInterval> | null = null;

function handleSend() {
  if (props.disabled || (!currentInput.value.trim() && !Object.keys(selectedMetadata.value).length)) {
    return;
  }

  const payload: MessagePayload = {
    content: currentInput.value.trim(),
    metadata: selectedMetadata.value,
  };

  emit("send", payload);
  currentInput.value = "";
  selectedMetadata.value = {};
}

function triggerAudioFileUpload() {
  audioFileInput.value?.click();
}

function triggerImageFileUpload() {
  imageFileInput.value?.click();
}

async function handleAudioFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];
    const payload: MessagePayload = {
      audioFile: file,
      metadata: selectedMetadata.value,
    };
    emit("send", payload);
    target.value = "";
    selectedMetadata.value = {};
  }
}

async function handleImageFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];
    const payload: MessagePayload = {
      imageFile: file,
      metadata: selectedMetadata.value,
    };
    emit("send", payload);
    target.value = "";
    selectedMetadata.value = {};
  }
}

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.value = new MediaRecorder(stream);
    audioChunks.value = []; // Clear previous chunks

    mediaRecorder.value.ondataavailable = (event) => {
      audioChunks.value.push(event.data);
    };

    mediaRecorder.value.onstop = () => {
      const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' });
      const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });

      // Send the recorded audio as a message
      const payload: MessagePayload = {
        audioFile: audioFile,
        metadata: selectedMetadata.value,
      };
      emit("send", payload);

      // Reset state
      isRecording.value = false;
      recordingTimer.value = 0;
      if (timerInterval) clearInterval(timerInterval);
      selectedMetadata.value = {}; // Reset metadata after sending
      stream.getTracks().forEach(track => track.stop()); // Stop microphone
    };

    mediaRecorder.value.start();
    isRecording.value = true;
    recordingTimer.value = 0;
    timerInterval = setInterval(() => {
      recordingTimer.value++;
    }, 1000);

  } catch (error) {
    console.error("Error accessing microphone or starting recording:", error);
    isRecording.value = false;
    recordingTimer.value = 0;
    if (timerInterval) clearInterval(timerInterval);
    // TODO: Display an error message to the user (e.g., using PrimeVue Toast)
  }
};

const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop();
  }
};

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
};
</script>

<template>
  <div class="input-area">
    <!-- Hidden File Inputs -->
    <input type="file" ref="audioFileInput" @change="handleAudioFileChange" accept="audio/*" style="display: none" />
    <input type="file" ref="imageFileInput" @change="handleImageFileChange" accept="image/*" style="display: none" />

    <!-- Toggle Recording Button -->
    <Button
      :icon="isRecording ? 'pi pi-stop-circle' : 'pi pi-microphone'"
      :class="{ 'p-button-danger': isRecording, 'p-button-text': !isRecording, 'p-button-rounded': true }"
      @click="isRecording ? stopRecording() : startRecording()"
      :disabled="disabled"
      v-tooltip.top="isRecording ? `Stop Recording (${formatDuration(recordingTimer)})` : 'Start Recording'"
    />

    <!-- Original Upload Audio Button (Only show if not recording) -->
    <Button
      v-if="!isRecording"
      icon="pi pi-headphones"
      class="p-button-rounded p-button-secondary p-button-text"
      @click="triggerAudioFileUpload"
      :disabled="disabled"
      v-tooltip.top="'Upload audio file'"
    />

    <!-- Upload Image Button -->
    <Button
      icon="pi pi-image"
      class="p-button-rounded p-button-secondary p-button-text"
      @click="triggerImageFileUpload"
      :disabled="disabled || isRecording"
      v-tooltip.top="'Attach image'"
    />

    <!-- Metadata Selector Button -->
    <MetadataSelector v-model="selectedMetadata" :disabled="disabled || isRecording" />

    <InputText
      v-model="currentInput"
      @keydown.enter="handleSend"
      :disabled="disabled || isRecording"
      placeholder="Type a message..."
      class="flex-grow-1"
    />
    <Button
      icon="pi pi-send"
      @click="handleSend"
      :disabled="disabled || isRecording || (!currentInput.trim() && !Object.keys(selectedMetadata).length)"
      v-tooltip.top="'Send message'"
    />
  </div>
</template>

<style scoped>
.input-area {
  padding: 1rem;
  display: flex;
  background-color: var(--p-content-background);
  gap: 0.5rem;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  border-top: 1px solid var(--p-surface-border);
  box-shadow: var(--p-shadow-1);
}

.flex-grow-1 {
  flex-grow: 1;
}

:deep(.p-tooltip-text) {
  font-size: 0.75rem;
  padding: 0.5rem 0.75rem;
}
</style>