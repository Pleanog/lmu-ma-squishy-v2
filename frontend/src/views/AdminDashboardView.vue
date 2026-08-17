<template>
  <div class="p-4 flex justify-content-center">
    <Card class="admin-card">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <div class="flex align-items-center gap-2">
            <h2 class="m-0">Admin Dashboard</h2>
            <Tag :value="autoRefresh ? 'Auto Refresh ON' : 'Auto Refresh OFF'" :severity="autoRefresh ? 'success' : 'secondary'" />
          </div>
          <div class="flex align-items-center gap-2">
            <Button label="Back to Chat" icon="pi pi-arrow-left" text @click="goBackToChat" />
            <Button label="Refresh" icon="pi pi-refresh" :loading="loading" @click="loadStatus" />
          </div>
        </div>
      </template>
      <template #content>
        <div class="flex flex-column gap-3">
          <small class="text-color-secondary">
            Überblick über Server-/Client-Zustand, Routing und Gemini-Aktivität für schnelles Debugging.
          </small>

          <div v-if="error" class="error-box">{{ error }}</div>

          <div v-if="status" class="status-grid">
            <div class="status-card">
              <h4>Clients</h4>
              <p>Total: {{ status.client_counts?.total ?? 0 }}</p>
              <p>Frontend: {{ status.client_counts?.frontend ?? 0 }}</p>
              <p>Hardware: {{ status.client_counts?.hardware ?? 0 }}</p>
              <p>Monitor: {{ status.client_counts?.monitor ?? 0 }}</p>
            </div>

            <div class="status-card">
              <h4>Gemini</h4>
              <p>Session Active: {{ status.gemini?.is_session_active ? 'Yes' : 'No' }}</p>
              <p>Last Activity: {{ formatSeconds(status.gemini?.seconds_since_last_activity) }} ago</p>
              <p>API Key Source: {{ status.gemini?.api_key?.source ?? 'unknown' }}</p>
            </div>

            <div class="status-card">
              <h4>Routing</h4>
              <p>Hardware Mic: {{ onOff(status.routing_config?.hardware_mic_enabled) }}</p>
              <p>Hardware Speaker: {{ onOff(status.routing_config?.hardware_speaker_enabled) }}</p>
              <p>UI Text Mode: {{ onOff(status.routing_config?.ui_text_mode_enabled) }}</p>
            </div>
          </div>

          <div v-if="status?.clients?.length" class="clients-list">
            <h4>Connected Clients</h4>
            <div v-for="client in status.clients" :key="client.client_id" class="client-item">
              <div class="flex align-items-center gap-2 flex-wrap">
                <Tag :value="client.client_type" severity="info" />
                <Tag v-if="client.is_active_controller" value="Active Controller" severity="contrast" />
                <span class="font-medium">{{ shortId(client.client_id) }}</span>
                <span class="text-color-secondary">{{ client.username || 'no-username' }}</span>
              </div>
              <small class="text-color-secondary">{{ (client.capabilities || []).join(', ') }}</small>
            </div>
          </div>

          <div class="flex align-items-center gap-2">
            <Checkbox v-model="autoRefresh" binary />
            <span class="text-sm text-color-secondary">Auto-refresh every 5 seconds</span>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import Button from 'primevue/button';
import Checkbox from 'primevue/checkbox';

const router = useRouter();
const loading = ref(false);
const error = ref('');
const status = ref<any>(null);
const autoRefresh = ref(true);
let refreshTimer: number | null = null;

function getApiBaseUrl(): string {
  if (typeof window === 'undefined') return 'http://127.0.0.1:8000';
  return window.location.origin;
}

function onOff(value: boolean | undefined): string {
  return value ? 'ON' : 'OFF';
}

function shortId(value: string): string {
  return (value || '').slice(0, 8);
}

function formatSeconds(raw: number | undefined): string {
  if (typeof raw !== 'number' || Number.isNaN(raw)) return 'n/a';
  return `${Math.max(0, Math.round(raw))}s`;
}

function goBackToChat(): void {
  router.push('/squishy');
}

async function loadStatus(): Promise<void> {
  loading.value = true;
  error.value = '';
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/admin/status`);
    if (!res.ok) {
      throw new Error(await res.text());
    }
    status.value = await res.json();
  } catch (e: any) {
    error.value = e?.message ?? String(e);
  } finally {
    loading.value = false;
  }
}

function startAutoRefresh(): void {
  stopAutoRefresh();
  refreshTimer = window.setInterval(() => {
    loadStatus();
  }, 5000);
}

function stopAutoRefresh(): void {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

watch(autoRefresh, (enabled) => {
  if (enabled) startAutoRefresh();
  else stopAutoRefresh();
});

onMounted(async () => {
  await loadStatus();
  if (autoRefresh.value) startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.admin-card {
  max-width: 1100px;
  width: 100%;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

.status-card {
  border: 1px solid var(--surface-200);
  border-radius: 0.75rem;
  padding: 0.75rem 0.9rem;
  background: rgba(148, 163, 184, 0.06);
}

.status-card h4 {
  margin: 0 0 0.45rem;
}

.status-card p {
  margin: 0.2rem 0;
}

.clients-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.client-item {
  border: 1px solid var(--surface-200);
  border-radius: 0.7rem;
  padding: 0.6rem 0.75rem;
}

.error-box {
  border: 1px solid rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
  border-radius: 0.6rem;
  padding: 0.55rem 0.75rem;
}
</style>
