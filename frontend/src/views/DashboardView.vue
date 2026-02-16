<script setup lang="ts">
import { ref } from "vue";
import { useAuth } from "../composables/useAuth";
import ChatInterface from "../components/ChatInterface.vue";
import ConversationList from "../components/ConversationList.vue";
import { useRouter } from "vue-router";

const router = useRouter();

const { currentUser, logout } = useAuth();

const selectedChatId = ref<string | null>(null);

function handleChatSelect(id: string) {
  selectedChatId.value = id;
}
</script>

<template>
  <div v-if="router.currentRoute.value.name === 'dashboard'">
    <div class="dashboard-layout">
      <!-- Header -->
      <header class="top-bar">
        <div class="brand">Squishy 2.0</div>
        <div class="user-actions">
          <span class="user-name">{{ currentUser?.email }}</span>
          <Button
            icon="pi pi-sign-out"
            class="p-button-rounded p-button-text p-button-danger"
            @click="logout"
          />
        </div>
      </header>

      <div class="main-content">
        <aside class="sidebar">
          <ConversationList
            :active-id="selectedChatId"
            @select="handleChatSelect"
          />
        </aside>

        <!-- Right Content: Chat -->
        <main class="chat-panel">
          <ChatInterface v-if="selectedChatId" :chat-id="selectedChatId" />
          <div v-else class="empty-state">
            <i class="pi pi-comments" style="font-size: 3rem; color: #ccc"></i>
            <p>Select a conversation or start a new one.</p>
          </div>
        </main>
      </div>
    </div>
  </div>
  <router-view v-else></router-view>
</template>

<style scoped>
.dashboard-layout {
  display: flex;
  flex-direction: column;
  height: 98vh;
  overflow: hidden;
}
.top-bar {
  height: 60px;
  background: white;
  border-bottom: 1px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
}
.brand {
  font-weight: bold;
  font-size: 1.2rem;
  color: #333;
}
.user-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.user-name {
  font-size: 0.9rem;
  color: #666;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  background: #f8f9fa;
  border-right: 1px solid #ddd;
}

.chat-panel {
  flex: 1;
  background: #fff;
  position: relative;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
}
</style>
