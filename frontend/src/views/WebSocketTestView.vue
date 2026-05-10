<template>
  <div class="p-4">
    <Card>
      <template #title>WebSocket Test (Frontend Companion App)</template>
      <template #content>
        <div class="flex flex-col gap-4">
          <div class="flex gap-2">
            <InputText v-model="wsUrl" placeholder="WebSocket URL" class="flex-grow" />
            <Button
              :label="isConnected ? 'Disconnect' : 'Connect'"
              :icon="isConnected ? 'pi pi-times' : 'pi pi-bolt'"
              :severity="isConnected ? 'danger' : 'success'"
              @click="toggleConnection"
              :loading="loading"
            />
          </div>

          <Message v-if="connectionError" severity="error">{{ connectionError }}</Message>
          <Message v-if="isConnected" severity="success">Connected to: {{ wsUrl }}</Message>
          <Message v-if="!isConnected && !connectionError" severity="info">Disconnected</Message>

          <div v-if="isConnected" class="flex flex-col gap-3 mt-4">
            <h4>Send Message:</h4>
            <div class="flex gap-2">
              <InputText v-model="messageToSend" placeholder="Enter text message" class="flex-grow" @keyup.enter="sendTextMessage" />
              <Button label="Send Text" icon="pi pi-send" @click="sendTextMessage" />
            </div>

            <Divider />

            <h4>Received Messages:</h4>
            <div class="bg-surface-800 text-white p-3 border-round max-h-96 overflow-auto">
              <div v-for="(msg, index) in receivedMessages" :key="index" class="mb-2">
                <span :class="{'text-primary-400': msg.type === 'sent', 'text-green-400': msg.type === 'received'}">
                  [{{ msg.timestamp }}] {{ msg.type.toUpperCase() }}:
                </span>
                <pre class="ml-4 whitespace-pre-wrap text-sm">{{ msg.content }}</pre>
              </div>
              <div v-if="!receivedMessages.length" class="text-surface-500">No messages received yet.</div>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import Card from 'primevue/card';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Divider from 'primevue/divider';
// const wsUrl = ref('ws://localhost:8000/ws'); // Default to your FastAPI frontend WebSocket
// const wsUrl = ref('http://127.0.0.1:8000/ws'); // Default to your FastAPI frontend WebSocket
const wsUrl = ref('ws://127.0.0.1:8000/ws');
const websocket = ref<WebSocket | null>(null);
const isConnected = ref(false);
const loading = ref(false);
const connectionError = ref('');
const messageToSend = ref('');
const receivedMessages = ref<Array<{ type: 'sent' | 'received'; content: string; timestamp: string }>>([]);

function logMessage(type: 'sent' | 'received', content: any) {
  receivedMessages.value.push({
    type,
    content: typeof content === 'string' ? content : JSON.stringify(content, null, 2),
    timestamp: new Date().toLocaleTimeString(),
  });
  // Auto-scroll to bottom
  nextTick(() => {
    const logContainer = document.querySelector('.max-h-96.overflow-auto');
    if (logContainer) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  });
}

async function toggleConnection() {
  if (isConnected.value) {
    disconnect();
  } else {
    await connect();
  }
}

async function connect() {
  loading.value = true;
  connectionError.value = '';
  receivedMessages.value = [];

  try {
    websocket.value = new WebSocket(wsUrl.value);

    websocket.value.onopen = () => {
      isConnected.value = true;
      loading.value = false;
      logMessage('received', 'WebSocket connection opened.');
    };

    websocket.value.onmessage = (event) => {
      logMessage('received', event.data);
    };

    websocket.value.onerror = (event) => {
      console.error('WebSocket error:', event);
      connectionError.value = 'WebSocket error. Check console for details.';
      isConnected.value = false;
      loading.value = false;
      logMessage('received', 'WebSocket error.');
    };

    websocket.value.onclose = (event) => {
      isConnected.value = false;
      loading.value = false;
      logMessage('received', `WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`);
      if (!event.wasClean) {
        connectionError.value = `Connection closed unexpectedly. Code: ${event.code}`;
      }
    };
  } catch (e: any) {
    connectionError.value = `Failed to create WebSocket: ${e.message}`;
    loading.value = false;
  }
}

function disconnect() {
  if (websocket.value) {
    websocket.value.close();
    websocket.value = null;
  }
}

function sendTextMessage() {
  if (websocket.value && isConnected.value && messageToSend.value) {
    logMessage('sent', messageToSend.value);
    websocket.value.send(messageToSend.value);
    messageToSend.value = '';
  }
}

onUnmounted(() => {
  disconnect(); // Ensure WebSocket is closed when component is unmounted
});
</script>

<style scoped>
/* Add any specific styles here if needed */
</style>