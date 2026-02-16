<script setup lang="ts">
import { ref, watch } from "vue";

const isDark = ref<boolean>(localStorage.getItem("theme") === "dark");

watch(isDark, (val: boolean) => {
  document.documentElement.classList.toggle("dark", val);
  localStorage.setItem("theme", val ? "dark" : "light");
});
</script>

<template>
  <Button
    rounded
    variant="outlined"
    :label="isDark ? 'Heller Modus' : 'Dunkler Modus'"
    severity="secondary"
    aria-label="Toggle Theme"
    @click="isDark = !isDark"
  >
    <template #icon>
      <component
        :is="!isDark ? 'SunIcon' : 'MoonIcon'"
        size="24"
        stroke-width="2"
      />
    </template>
  </Button>
</template>
