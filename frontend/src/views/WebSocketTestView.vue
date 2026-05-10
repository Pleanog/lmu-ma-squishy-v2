<template>
  <div class="p-4">
    <Card>
      <template #title>WebSocket Test (Frontend Companion App)</template>
      <template #content>
        <h4>Live Transcript:</h4>

        <div class="transcript-box">
        {{ liveTranscript || 'Waiting for transcription...' }}
        </div>

        ...

        <div
            v-if="partialTranscript"
            class="bg-surface-900 text-white p-4 border-round"
            >
            <h3 class="mb-2">Live Transcript</h3>

            <div class="text-lg line-height-3" style="color: black">
                {{ partialTranscript }}
            </div>
        </div>

        <audio ref="audioPlayer" controls class="w-full mt-3"></audio>

        <Divider />
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
            <div class="log-container">
            <div
                v-for="(msg, index) in receivedMessages"
                :key="index"
                class="log-entry"
            >
                <div
                :class="msg.type === 'sent' ? 'log-sent' : 'log-received'"
                >
                [{{ msg.timestamp }}] {{ msg.type.toUpperCase() }}
                </div>

                <pre class="log-content">{{ msg.content }}</pre>
            </div>

            <div v-if="!receivedMessages.length">
                No messages received yet.
            </div>
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
const liveTranscript = ref('');
const partialTranscript = ref('');
const audioChunks = ref<Blob[]>([]);
const audioPlayer = ref<HTMLAudioElement | null>(null);

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

    websocket.value.onmessage = async (event) => {
        console.log('RAW WS MESSAGE:', event.data);
        console.log(event.data.type);

        // AUDIO CHUNK
        if (event.data instanceof Blob) {
            console.log('AUDIO CHUNK:', event.data.size);

            audioChunks.value.push(event.data);

            return;
        }

        try {
            const parsed = JSON.parse(event.data);

            console.log('PARSED WS MESSAGE:', parsed);

            if (parsed.type === 'gemini' && parsed.text) {
            partialTranscript.value += parsed.text;
            }

            if (parsed.type === 'turn_complete') {
            logMessage('received', partialTranscript.value);

            // AUDIO ABSPIELEN
            playCollectedAudio();

            partialTranscript.value = '';
            }
        } catch (err) {
            console.error('Failed to parse websocket message', err);
        }
    };

    function playCollectedAudio() {
        if (!audioChunks.value.length) return;

        // WAV ausprobieren
        const audioBlob = new Blob(audioChunks.value, {
            type: 'audio/wav',
        });

        const audioUrl = URL.createObjectURL(audioBlob);

        if (audioPlayer.value) {
            audioPlayer.value.src = audioUrl;
            audioPlayer.value.play();
        }

        // reset
        audioChunks.value = [];
    }

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