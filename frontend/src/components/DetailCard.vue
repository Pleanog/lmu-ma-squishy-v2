<template>
  <PCard
    :class="['detail-card', { 'limited-height': showMoreButton }]"
    v-bind="attrs"
  >
    <template #title>{{ title || t(generic.details) }}</template>

    <template #content>
      <div v-if="hasError" class="error-state-container">
        <EmptyState
          :image="errorObject?.image || 'error.png'"
          :title="
            errorObject?.title || t('generic.status.data_load_failed_title')
          "
          :subtitle="
            errorObject?.subtitle || t('generic.status.try_again_later_hint')
          "
        >
        </EmptyState>
      </div>

      <div v-else-if="isLoading" class="loading-state-container">
        <div v-for="i in maxRows" :key="i" class="detail-row">
          <PSkeleton width="69%" height="1.2rem" />
          <PSkeleton width="29%" height="1.2rem" />
        </div>
      </div>

      <div v-else class="content-wrapper">
        <div
          v-for="(item, index) in limitedData"
          :key="index"
          class="detail-row"
        >
          <span>{{ item.label }}</span>

          <slot :name="item.key" :item="item">
            <span>{{ item.value }}</span>
          </slot>
        </div>

        <div v-if="showMoreButton" class="show-more-overlay">
          <PButton
            :label="t('generic.action.show_all_details')"
            severity="secondary"
            outlined
            @click="openModal"
          >
            <template #icon>
              <component :is="'ExpandIcon'" size="18" stroke-width="1.5" />
            </template>
          </PButton>
        </div>
      </div>
    </template>
  </PCard>

  <PDialog
    v-model:visible="isModalVisible"
    :header="title"
    modal
    :pt="dialogPT"
    :maximizable="!isMaximizedOnMobile"
    :draggable="false"
    :style="{ width: modalWidth }"
  >
    <div
      v-for="(item, index) in data"
      :key="'modal-' + index"
      class="detail-row"
    >
      <span>{{ item.label }}</span>
      <slot :name="item.key" :item="item">
        <span>{{ item.value }}</span>
      </slot>
    </div>
  </PDialog>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

import { ref, computed, useAttrs, onMounted, onUnmounted } from "vue";
import { useI18n } from "vue-i18n";
const { t } = useI18n();

const props = defineProps({
  title: {
    type: String,
    required: false,
  },
  data: {
    type: Array,
    required: true,
  },
  maxRows: {
    type: Number,
    default: 5,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  hasError: {
    type: Boolean,
    default: false,
  },
  errorObject: {
    type: Object,
    required: false,
    validator: (value) => {
      return (
        value === null || (typeof value === "object" && "message" in value)
      );
    },
  },
  modalWidth: {
    type: String,
    default: "40vw",
  },
});

const attrs = useAttrs();

const isModalVisible = ref(false);

const openModal = () => {
  isModalVisible.value = true;
};

const showMoreButton = computed(() => {
  return props.data.length > props.maxRows;
});

const limitedData = computed(() => {
  if (!showMoreButton.value) {
    return props.data;
  }
  return props.data.slice(0, props.maxRows);
});

// Responsive Maximized State für Mobile

const screenWidth = ref(window.innerWidth);
const mobileBreakpoint = 768;

const updateWidth = () => {
  screenWidth.value = window.innerWidth;
};

onMounted(() => {
  window.addEventListener("resize", updateWidth, { passive: true });
});

onUnmounted(() => {
  window.removeEventListener("resize", updateWidth);
});

const isMaximizedOnMobile = computed(() => {
  return screenWidth.value <= mobileBreakpoint;
});

const dialogPT = computed(() => {
  if (isMaximizedOnMobile.value) {
    return {
      root: { class: "p-dialog-maximized" },
      mask: { class: "p-dialog-maximized" },
    };
  }
  return {};
});
</script>

<style lang="scss" scoped>
.content-wrapper {
  position: relative;
  padding-bottom: 0.5rem;
}

.detail-row {
  display: flex;
  // justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
  font-size: 0.95rem;
  overflow: hidden;
  font-weight: 500;

  &:last-child {
    border-bottom: none;
  }

  span:first-child {
    font-weight: 400;
    color: var(--p-text-muted-color);
    width: 14rem;
  }
}

.show-more-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  background: linear-gradient(
    to top,
    var(--p-card-background) 50%,
    transparent 100%
  );
  padding-top: 2rem;
  padding-bottom: 0.5rem;
  z-index: 10;
}
</style>
