<script setup lang="ts">
import { onMounted } from "vue";
import { useConversations } from "../composables/useConversations";
import { useRouter, useRoute } from "vue-router";

const router = useRouter();

// Props: ID of currently selected chat (for highlighting)
defineProps<{
  activeId: string | null;
}>();

// Emits: When user clicks a button
const emit = defineEmits<{
  (e: "select", id: string): void;
}>();

const { conversations, fetchConversations, createConversation, loading } =
  useConversations();

async function handleNewChat() {
  const newChat = await createConversation(
    `Chat ${new Date().toLocaleTimeString()}`,
  );
  if (newChat) {
    emit("select", newChat.id);
  }
}

const navigateToSettings = () => {
  router.push({ name: "settings" });
};

onMounted(() => {
  fetchConversations();
});
</script>

<template>
  <div class="list-container">
    <Button
      label="New Chat"
      icon="pi pi-plus"
      class="w-full mb-3 p-button-outlined"
      @click="handleNewChat"
      :loading="loading"
    />

    <div class="scroll-list">
      <div v-if="conversations.length === 0" class="empty-text">
        No chats yet.
      </div>

      <button
        v-for="chat in conversations"
        :key="chat.id"
        class="chat-btn"
        :class="{ active: chat.id === activeId }"
        @click="emit('select', chat.id)"
      >
        <i class="pi pi-comments"></i>
        <span class="chat-title">{{ chat.title }}</span>
      </button>
    </div>
    <Button
      label="Settings"
      icon="pi pi-cog"
      class="w-full mb-3 p-button-outlined"
      @click="navigateToSettings"
      :loading="loading"
    />
  </div>
</template>

<style scoped>
.list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 1rem;
  border-right: 1px solid #ddd;
  background-color: var(--p-content-background);
}
.scroll-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.chat-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s;
  width: 100%;
}
.chat-btn:hover {
  background: var(--p-button-text-plain-hover-background);
}
.chat-btn.active {
  background-color: var(--p-button-outlined-secondary-active-background);
  color: var(--p-button-text-plain-color);
  font-weight: bold;
}
.chat-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.w-full {
  width: 100%;
}
.mb-3 {
  margin-bottom: 1rem;
}
.empty-text {
  text-align: center;
  color: #888;
  margin-top: 1rem;
  font-size: 0.9rem;
}
</style>
