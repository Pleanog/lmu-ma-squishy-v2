// src/views/ChatView.vue (or your main chat file)
<script setup lang="ts">
import { ref, toRef, nextTick, watch } from "vue";
import { useChat } from "../composables/useChat";
import type { MessagePayload } from "../types";

const props = defineProps<{
  chatId: string;
}>();

const { messages, currentChatTitle, sendMessage, loadingMessages, getFileUrl, } = useChat(
  toRef(props, "chatId"),
);

const chatContainer = ref<HTMLElement | null>(null);

// Handle sending message from MessageInput component
async function handleSendMessage(payload: MessagePayload) {
  await sendMessage(payload);
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
  <div class="chat-wrapper surface-ground">
    <!-- Header -->
    <div class="chat-header surface-card">
      <h3>{{ currentChatTitle || "Loading..." }}</h3>
      <small class="id-text">ID: {{ chatId }}</small>
    </div>

    <!-- Messages Area -->
    <div class="messages-container" ref="chatContainer">
      <div v-if="loadingMessages" class="loading-state">
        <ProgressSpinner style="width: 30px; height: 30px" strokeWidth="4" animationDuration=".8s" aria-label="Loading"/>
        Loading history...
      </div>

      <template v-else>
        <ChatBubble
          v-for="msg in messages"
          :key="msg.id"
          :msg="msg"
          :getFileUrl="getFileUrl"
        />
      </template>
    </div>

    <!-- Input Area -->
    <div class="input-container" >
      <MessageInput :disabled="loadingMessages" @send="handleSendMessage" />
    </div>
  </div>
</template>

<style scoped>
.chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: var(--p-shadow-2);
  border-radius: var(--p-border-radius);
  overflow: hidden;
}
.chat-header {
  padding: 1rem;
  border-bottom: 1px solid var(--p-surface-border);
  box-shadow: var(--p-shadow-1);
  z-index: 1; /* Ensure header stays above messages */
}
.chat-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--p-text-color);
}
.id-text {
  color: var(--p-text-secondary-color);
  font-size: 0.7rem;
}

.messages-container {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background-color: var(--p-surface-ground);
  padding-left: 20%;
  padding-right: 20%;
}

.input-container {
  padding-left: 20%;
  padding-right: 20%;
}

/* For smaller screens, adjust padding */
@media (max-width: 768px) {
  .messages-container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
  .input-container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

.loading-state {
  text-align: center;
  color: var(--p-text-secondary-color);
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}
</style>