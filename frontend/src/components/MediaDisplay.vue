<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import type { SliderSlideEndEvent } from 'primevue/slider';

const props = defineProps<{
  audioUrl?: string; // Optional URL for audio
  imageUrl?: string; // Optional URL for image
  altText?: string; // Alt text for image
}>();

// --- Audio Playback Logic ---
const audioRef = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);

const togglePlayPause = () => {
  if (audioRef.value) {
    if (isPlaying.value) {
      audioRef.value.pause();
    } else {
      audioRef.value.play();
    }
    isPlaying.value = !isPlaying.value;
  }
};

const onTimeUpdate = () => {
  if (audioRef.value) {
    currentTime.value = audioRef.value.currentTime;
  }
};

const onLoadedMetadata = () => {
  if (audioRef.value) {
    duration.value = audioRef.value.duration;
  }
};

const onEnded = () => {
  isPlaying.value = false;
  currentTime.value = 0;
};

const seekAudio = (event: SliderSlideEndEvent) => {
  if (audioRef.value && typeof event.value === 'number') {
    audioRef.value.currentTime = event.value;
  }
};

// Clean up event listeners on unmount
onMounted(() => {
  if (audioRef.value) {
    audioRef.value.addEventListener("timeupdate", onTimeUpdate);
    audioRef.value.addEventListener("loadedmetadata", onLoadedMetadata);
    audioRef.value.addEventListener("ended", onEnded);
  }
});

onUnmounted(() => {
  if (audioRef.value) {
    audioRef.value.removeEventListener("timeupdate", onTimeUpdate);
    audioRef.value.removeEventListener("loadedmetadata", onLoadedMetadata);
    audioRef.value.removeEventListener("ended", onEnded);
  }
});

// Format time for display
const formatTime = (seconds: number) => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
};

// --- Conditional Display ---
const hasMedia = computed(() => props.audioUrl || props.imageUrl);
</script>

<template>
  <div class="media-display">
    <template v-if="props.audioUrl">
      <div class="audio-player p-card">
        <audio ref="audioRef" :src="props.audioUrl" preload="metadata"></audio>

        <div class="audio-controls flex align-items-center gap-2">
          <Button
            :icon="isPlaying ? 'pi pi-pause' : 'pi pi-play'"
            class="p-button-rounded p-button-text p-button-sm"
            @click="togglePlayPause"
            :disabled="!duration"
          />

          <div class="audio-progress flex-grow-1 flex align-items-center gap-2">
            <span class="p-text-secondary text-xs">{{ formatTime(currentTime)}}</span>
            <Slider
              v-model="currentTime"
              :min="0"
              :max="duration"
              :step="0.1"
              @slideend="seekAudio"
              class="w-full"
            />
            <span class="p-text-secondary text-xs">{{ formatTime(duration) }}</span>
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="props.imageUrl">
      <div class="image-viewer p-card">
        <Image
          :src="props.imageUrl"
          :alt="props.altText || 'Attached image'"
          imageClass="attached-image-preview"
          :preview="true"
        />
      </div>
    </template>

    <template v-else>
      <div class="no-media-placeholder p-text-secondary">
        No media attached.
      </div>
    </template>
  </div>
</template>

<style scoped>
.media-display {
  margin-top: 0.5rem; /* Space from message content */
  width: 100%; /* Occupy full width of bubble */
  max-width: 480px; /* Max width for consistency */
}

/* Base card styling for media containers */
.p-card {
  background-color: var(--p-surface-card);
  border-radius: var(--p-border-radius);
  padding: 0.75rem;
  box-shadow: var(--p-shadow-1);
}

/* Audio Player */
.audio-player {
  display: flex;
  flex-direction: column;
  background-color: var(--p-primary-50);
  border-radius: 12px;
  border: 1px solid var(--p-primary-200);;
}

audio {
  display: none; /* Hide default audio controls */
}

.audio-controls {
  width: 100%;
}

.audio-progress {
  min-width: 200px;
  width: 100%;
}

/* Image Viewer */
.image-viewer {
  display: flex;
  justify-content: center;
  align-items: center;
  max-width: 100%;
  border-radius: 12px;
  overflow: hidden;
  padding: 0;
}

/* Attached Image Preview within the bubble */
.attached-image-preview {
  padding: 0;
  margin: 0;
  max-width: 100%;
  height: auto;
  border-radius: var(--p-border-radius); /* Use PrimeVue variable for consistency */
  display: block; /* Remove extra space below image */
  object-fit: contain; /* Ensure image fits well */
  overflow: hidden; /* Ensure rounded corners clip */
  
}

/* No Media Placeholder */
.no-media-placeholder {
  text-align: center;
  font-style: italic;
  border: 1px dashed var(--p-surface-border);
  border-radius: var(--p-border-radius);
}

/* Flex utility classes (if not globally available via a utility library like PrimeFlex) */
.flex { display: flex; }
.align-items-center { align-items: center; }
.gap-2 { gap: 0.5rem; }
.flex-grow-1 { flex-grow: 1; }
.text-xs { font-size: 0.75rem; }
.w-full { width: 100%; margin-left: 10px;}
</style>