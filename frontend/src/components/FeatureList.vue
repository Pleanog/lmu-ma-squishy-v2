<template>
  <Card>
    <template #content>
      <div class="settings-list-wrapper">
        <div
          v-for="(item, index) in items"
          :key="index"
          class="settings-list-item"
          :class="{ 'is-clickable': isItemClickable(item) }"
          @click="handleRowClick(item)"
        >
          <!-- Text Content -->
          <div class="list-item-content">
            <div class="list-item-title" :class="item.titleClass">
              {{ item.title }}
            </div>
            <div v-if="item.description" class="list-item-description">
              {{ item.description }}
            </div>
          </div>

          <!-- Action / Icon Area -->
          <div class="list-item-action" @click.stop>
            <!-- 1. Custom Component (e.g. Switch, Input) -->
            <component
              v-if="item.component"
              :is="item.component"
              v-bind="item.componentProps"
            />

            <!-- 2. Navigation Icon (Lucide) -->
            <!-- We check for 'to' or 'onClick'. We use item.icon if provided, else default to ChevronRight -->
            <component
              v-else-if="item.to || item.onClick"
              :is="item.icon || ChevronRight"
              :size="20"
              :stroke-width="2"
              class="navigation-icon"
            />
          </div>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { type Component } from "vue";
import { useRouter } from "vue-router";

// 1. Import PrimeVue Components explicitly
import Card from "primevue/card";

// 2. Import a default icon for the fallback
import { ChevronRight } from "lucide-vue-next";

// 3. Define Types
export interface SettingsItem {
  title: string;
  description?: string;
  titleClass?: string;
  // Navigation
  to?: string; // Route name
  params?: Record<string, any>; // Route params
  onClick?: () => void;
  // Icons & Components
  icon?: string | Component; // Can be a string name (if global) or an import
  component?: Component | string; // Custom component (like a Switch)
  componentProps?: Record<string, any>;
}

// 4. Props Definition
const props = defineProps<{
  items: SettingsItem[];
}>();

const router = useRouter();

// 5. Logic
const isItemClickable = (item: SettingsItem): boolean => {
  // It's clickable if it has an action/route AND it's not an interactive form component
  return !!((item.to || item.onClick) && !item.component);
};

const handleRowClick = (item: SettingsItem) => {
  // If there is a custom component (like a switch), we usually don't want the row click to trigger navigation
  if (item.component) return;

  if (item.onClick) {
    item.onClick();
    return;
  }

  if (item.to) {
    // Check if router exists (safety)
    if (router) {
      router.push({ name: item.to, params: item.params || {} });
    } else {
      console.warn("Router instance not found");
    }
  }
};
</script>

<style scoped>
/* Basic layout styles to make the flex logic work */
.settings-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.settings-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border, #e5e7eb);
  transition: background-color 0.2s;
}

.settings-list-item:last-child {
  border-bottom: none;
}

.settings-list-item.is-clickable {
  cursor: pointer;
}

.settings-list-item.is-clickable:hover {
  background-color: var(--surface-hover, #f3f4f6);
}

.list-item-content {
  display: flex;
  flex-direction: column;
}

.list-item-title {
  font-weight: 600;
  font-size: 1rem;
}

.list-item-description {
  font-size: 0.875rem;
  color: var(--text-color-secondary, #6b7280);
  margin-top: 0.25rem;
}

.list-item-action {
  display: flex;
  align-items: center;
  margin-left: 1rem;
}

.navigation-icon {
  color: var(--text-color-secondary, #9ca3af);
}
</style>
