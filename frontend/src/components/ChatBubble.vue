// src/components/ChatBubble.vue
<script setup lang="ts">
import { computed } from "vue";
import type { Message, MessageMetadata, Sender } from "../types";
import { formatTimestamp } from "../utils/timeUtils";

const props = defineProps<{
  msg: Message;
  getFileUrl: (msg: Message, field: "audio" | "image") => string | undefined;
}>();

const isUserMessage = computed(() => props.msg.sender === "user");
const hasMetadata = computed(
  () =>
    isUserMessage.value &&
    props.msg.metadata &&
    Object.keys(props.msg.metadata).length > 0,
);

const formattedMetadata = computed(() => {
  if (!props.msg.metadata) return "";
  return Object.entries(props.msg.metadata)
    .map(([key, value]) => {
      const formattedKey = key
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, (str) => str.toUpperCase());
      const formattedValue = typeof value === "boolean" ? (value ? "Yes" : "No") : value;
      return `${formattedKey}: ${formattedValue}`;
    })
    .join("\n");
});

const audioUrl = computed(() => props.getFileUrl(props.msg, 'audio'));
const imageUrl = computed(() => props.getFileUrl(props.msg, 'image'));
</script>

<template>
  <div
    :class="['bubble', isUserMessage ? 'my-msg' : 'ai-msg']"
    v-tooltip="hasMetadata ? { value: formattedMetadata, escape: true } : null"
  >

    <!-- Message content (if any) -->
    <div v-if="msg.content">{{ msg.content }}</div>

    <!-- Media Display Component -->
    <MediaDisplay
      v-if="audioUrl || imageUrl"
      :audio-url="audioUrl"
      :image-url="imageUrl"
      :alt-text="msg.content || 'Attached media'"
    />
    <!-- The MediaDisplay component handles 'No media attached' internally if neither URL is provided -->

    <div class="additional_info">
      {{ formatTimestamp(msg.created) }}
        <i
        v-if="hasMetadata"
        class="pi pi-info-circle metadata-icon"
      ></i>
    </div>
  </div>
</template>


<style scoped>
.bubble {
  padding: 0.8rem;
  border-radius: 12px;
  position: relative;
  font-size: 0.95rem;
  line-height: 1.4;
  max-width: 70%; /* Keep max-width here */
  word-wrap: break-word; /* Ensure long words wrap */
}
.my-msg {
  text-align: right;
  align-self: flex-end;
  background-color: var(--p-primary-50); 
  color: var(--p-primary-900);
  border-bottom-right-radius: 2px;
  margin-left: auto; /* Push to the right */
}
.ai-msg {
  text-align: left !important;
  background-color: red;
  align-self: flex-start;
  background-color: var(--p-content-background); /* PrimeVue background for AI messages */
  color: var(--p-text-color);
  border-bottom-left-radius: 2px;
  margin-right: auto; /* Push to the left */
}

.ai-msg .sender-name {
  justify-content: flex-start; /* Align sender name to left for AI messages */
}

.metadata-icon {
  font-size: 0.6rem;
  color: var(--p-primary-400);
  cursor: help;
}
.additional_info {
  font-size: 0.65rem;
  margin-top: 0.3rem;
  opacity: 0.7;
  text-align: inherit;
  align-items: center;
  display: flex;
  gap: 0.3rem;
  justify-content: flex-end;
}


</style>