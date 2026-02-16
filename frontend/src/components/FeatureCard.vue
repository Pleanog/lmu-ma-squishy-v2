<template>
  <div class="navigation-card-wrapper cursor-pointer" @click="emit('click')">
    <PCard class="navigation-card">
      <template #content>
        <div class="card-content-wrapper">
          <div class="icon-container">
            <component
              :is="iconName"
              class="card-icon"
              :size="iconSize"
              stroke-width="1.5"
            />
          </div>

          <div class="card-text-content">
            <div class="card-title">{{ title }}</div>
            <div class="card-description">{{ description }}</div>
          </div>
        </div>
      </template>
    </PCard>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits(["click"]);

const props = defineProps({
  iconName: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  iconSize: {
    type: [Number, String],
    default: 32,
  },
});
</script>

<style lang="scss" scoped>
.navigation-card {
  width: 100%;
  height: 100%;
  &:hover {
    background-color: var(--p-button-text-primary-hover-background);
    cursor: pointer;
  }
}

.card-content-wrapper {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  grid-template-areas:
    "icon "
    "title"
    "description";
  gap: 0.25rem 1rem;
  padding: 0.5rem;
}

.icon-container {
  grid-area: icon;
  align-self: start;
  padding-top: 0.1rem;
}

.card-icon {
}

.card-text-content {
  min-width: 0;
  grid-area: title / title / description / description;
}

.card-title {
  grid-area: title;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--p-text-color);
  line-height: 1.3;
}

.card-description {
  grid-area: description;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}
</style>
