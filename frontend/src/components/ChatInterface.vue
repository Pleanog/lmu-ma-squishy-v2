<script setup lang="ts">
import { ref, toRef, nextTick, watch } from "vue";
import { useChat } from "../composables/useChat";
import { pb } from "../lib/pocketbase"; // Import pb to construct URLs

const props = defineProps<{
  chatId: string;
}>();

// Pass the prop as a ref to the composable so it reacts to changes
const { messages, currentChatTitle, sendMessage, loadingMessages } = useChat(
  toRef(props, "chatId"),
);

// Audio Upload Logic
const fileInput = ref<HTMLInputElement | null>(null);

const currentInput = ref("");
const chatContainer = ref<HTMLElement | null>(null);

function handleSend() {
  sendMessage(currentInput.value);
  currentInput.value = "";
}

function triggerFileUpload() {
  fileInput.value?.click();
}

async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];

    // Send message with file (We need to update useChat to support this,
    // or do it manually here for the prototype)
    try {
      const formData = new FormData();
      formData.append("conversation", props.chatId);
      formData.append("sender", "user");
      formData.append("audio", file);

      await pb.collection("messages").create(formData);
      // No need to push, realtime handles it
    } catch (e) {
      console.error(e);
    }

    // Clear input
    target.value = "";
  }
}

// Helper to get audio URL
function getAudioUrl(msg: any) {
  return `${pb.baseUrl}/api/files/${msg.collectionId}/${msg.id}/${msg.audio}`;
}

// Auto-scroll when messages change
watch(
  messages,
  () => {
    nextTick(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
      }
    });
  },
  { deep: true },
);
</script>

<template>
  <div class="chat-wrapper">
    <!-- Header -->
    <div class="chat-header">
      <h3>{{ currentChatTitle || "Loading..." }}</h3>
      <small class="id-text">ID: {{ chatId }}</small>
    </div>

    <!-- Messages Area -->
    <div class="messages-container" ref="chatContainer">
      <div v-if="loadingMessages" class="loading-state">
        <i class="pi pi-spinner pi-spin"></i> Loading history...
      </div>

      <div
        v-else
        v-for="msg in messages"
        :key="msg.id"
        :class="['bubble', msg.sender === 'user' ? 'my-msg' : 'ai-msg']"
      >
        <div class="sender-name">
          {{ msg.sender }}
        </div>
        <div>{{ msg.content }}</div>
        <audio
          v-if="msg.audio && msg.audio.length > 0"
          :src="getAudioUrl(msg)"
          controls
        ></audio>
        <div class="time">
          {{
            new Date(msg.created).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })
          }}
        </div>
      </div>
    </div>

    <div class="input-area">
      <!-- Hidden File Input -->
      <input
        type="file"
        ref="fileInput"
        @change="handleFileChange"
        accept="audio/*"
        style="display: none"
      />

      <!-- Upload Button -->
      <Button
        icon="pi pi-microphone"
        class="p-button-rounded p-button-secondary p-button-text"
        @click="triggerFileUpload"
      />

      <InputText
        v-model="currentInput"
        @keydown.enter="handleSend"
        :disabled="loadingMessages"
        placeholder="Type a message..."
        fluid
      />
      <Button
        icon="pi pi-send"
        @click="handleSend"
        :disabled="loadingMessages"
      />
    </div>
  </div>
</template>

<style scoped>
.chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%; /* Fill parent */
  background: #fff;
}
.chat-header {
  padding: 1rem;
  border-bottom: 1px solid #eee;
  background: #fff;
}
.chat-header h3 {
  margin: 0;
  font-size: 1.1rem;
}
.id-text {
  color: #aaa;
  font-size: 0.7rem;
}

.messages-container {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background-color: #f0f2f5;
  padding-left: 25%;
  padding-right: 25%;
}
.input-area {
  padding: 1rem;
  display: flex;
  background-color: #f0f2f5;
  gap: 0.5rem;
  padding-left: 25%;
  padding-right: 25%;
}

.bubble {
  padding: 0.8rem;
  border-radius: 12px;
  position: relative;
  font-size: 0.95rem;
  line-height: 1.4;
}
.my-msg {
  text-align: right;
  max-width: 70%;
  align-self: flex-end;
  background-color: var(--p-content-background);
  border-bottom-right-radius: 2px;
}
.ai-msg {
  text-align: left;
  align-self: flex-start;
  color: #333;
}
.sender-name {
  font-size: 0.7rem;
  margin-bottom: 0.2rem;
  opacity: 0.8;
  font-weight: bold;
}
.time {
  font-size: 0.65rem;
  text-align: right;
  margin-top: 0.3rem;
  opacity: 0.7;
}
.loading-state {
  text-align: center;
  color: #999;
  margin-top: 2rem;
}
</style>
