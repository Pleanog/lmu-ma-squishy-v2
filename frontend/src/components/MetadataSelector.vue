// src/components/MetadataSelector.vue
<script setup lang="ts">
import { ref, watch } from "vue";
import OverlayPanel from "primevue/overlaypanel";
import type { MessageMetadata } from "../types";

const emit = defineEmits(["update:modelValue"]);

const op = ref<InstanceType<typeof OverlayPanel> | null>(null);

const toggle = (event: Event) => {
  op.value?.toggle(event);
};

// Internal state for metadata selection
const internalMetadata = ref<MessageMetadata>({});

// Expose internal state via modelValue (v-model)
const props = defineProps<{
  modelValue: MessageMetadata;
}>();

watch(
  () => props.modelValue,
  (newVal) => {
    // Only update if external modelValue changes and it's different from internal
    if (JSON.stringify(newVal) !== JSON.stringify(internalMetadata.value)) {
      internalMetadata.value = { ...newVal };
    }
  },
  { immediate: true, deep: true },
);

watch(
  internalMetadata,
  (newVal) => {
    emit("update:modelValue", newVal);
  },
  { deep: true },
);

const brightnessOptions = ["dark", "normal", "bright"];

const resetMetadata = () => {
  internalMetadata.value = {};
};
</script>

<template>
  <Button
    icon="pi pi-tags"
    class="p-button-rounded p-button-secondary p-button-text"
    @click="toggle"
    aria-haspopup
    aria-controls="overlay_panel"
  />

  <OverlayPanel ref="op" appendTo="body" :showCloseIcon="true" id="overlay_panel">
    <div class="metadata-selection-panel">
      <h5>Attach Metadata</h5>
      <div class="p-field">
        <label for="brightness">Brightness</label>
        <Dropdown
          id="brightness"
          v-model="internalMetadata.brightness"
          :options="brightnessOptions"
          placeholder="Select brightness"
          showClear
          class="w-full"
        />
      </div>
      <div class="p-field flex align-items-center mt-3">
        <InputSwitch id="shaken" v-model="internalMetadata.shaken" />
        <label for="shaken" class="ml-2">Shaken</label>
      </div>

      <div class="flex justify-content-end mt-4">
        <Button
          label="Clear"
          icon="pi pi-times"
          class="p-button-text p-button-sm"
          @click="resetMetadata"
        />
      </div>
    </div>
  </OverlayPanel>
</template>

<style scoped>
.metadata-selection-panel {
  padding: 1rem;
  width: 250px; /* Fixed width for the panel */
}
.metadata-selection-panel h5 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  color: var(--p-text-color);
}
.p-field {
  margin-bottom: 0.75rem;
}
.p-field label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.85rem;
  color: var(--p-text-secondary-color);
}
/* Flex utility classes for PrimeVue 3.x if not using a utility library */
.flex { display: flex; }
.align-items-center { align-items: center; }
.mt-3 { margin-top: 0.75rem; }
.mt-4 { margin-top: 1rem; }
.ml-2 { margin-left: 0.5rem; }
.justify-content-end { justify-content: flex-end; }
.w-full { width: 100%; }
</style>