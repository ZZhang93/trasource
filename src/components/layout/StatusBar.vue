<template>
  <footer class="status-bar">
    <span class="status-dot" :class="backendOk ? 'dot-ok' : 'dot-err'" />
    <span class="status-item">{{ backendStatus }}</span>
    <span class="sep">│</span>
    <span class="status-item">{{ currentProject }}</span>
    <template v-if="recordCount">
      <span class="sep">│</span>
      <span class="status-item">{{ recordCount }} {{ t('format.records') }}</span>
    </template>
    <div class="flex-1" />
    <span class="status-item provider-tag">{{ providerLabel }}</span>
    <span class="sep">│</span>
    <span class="status-item model-name">{{ modelDisplay }}</span>
  </footer>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useBackendStore } from '@/stores/backend'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'

const { t } = useI18n()

const projectStore = useProjectStore()
const backend = useBackendStore()
const backendOk = computed(() => backend.ready)
const backendStatus = computed(() =>
  t(backend.ready ? 'status.ready' : backend.failed ? 'status.offline' : 'status.starting')
)
const providerLabel = ref('Gemini')
const expansionModelLabel = ref('')
const extractionModelLabel = ref('')

function getProviderLabel(p: string): string {
  const STATIC: Record<string, string> = {
    gemini: 'Gemini',
    claude: 'Claude',
    openai: 'ChatGPT',
    deepseek: 'DeepSeek',
  }
  if (p === 'openai_compatible') return t('status.localModel')
  return STATIC[p] || p
}

function getModelLabel(provider: string, modelId: string): string {
  if (!modelId) return t('status.notConfigured')
  // 对于已知模型，显示简短名
  const SHORT: Record<string, string> = {
    'gemini-2.5-flash': '2.5 Flash',
    'gemini-2.5-pro': '2.5 Pro',
    'gemini-3-flash-preview': '3 Flash',
    'gemini-3.1-flash-lite-preview': '3.1 Flash Lite',
    'gemini-3.1-pro-preview': '3.1 Pro',
    'claude-haiku-4-5-20251001': 'Haiku 4.5',
    'claude-sonnet-4-6': 'Sonnet 4.6',
    'claude-opus-4-6': 'Opus 4.6',
    'gpt-4o-mini': '4o Mini',
    'gpt-4o': '4o',
    'gpt-4.1': '4.1',
    'gpt-4.1-mini': '4.1 Mini',
    'gpt-4.1-nano': '4.1 Nano',
    'o3-mini': 'o3 Mini',
    'gpt-5': '5',
    'gpt-5-mini': '5 Mini',
    'gpt-5.1': '5.1',
    'claude-sonnet-5': 'Sonnet 5',
    'claude-opus-4-8': 'Opus 4.8',
    'deepseek-chat': 'Chat (V3)',
    'deepseek-reasoner': 'Reasoner (R1)',
  }
  return SHORT[modelId] || modelId
}

const PROVIDER_PREFIX: Record<string, string> = {
  gemini: 'gemini', claude: 'claude', openai: 'openai',
  deepseek: 'deepseek', openai_compatible: 'local',
}
const PROVIDER_DEFAULT: Record<string, string> = {
  gemini: 'gemini-3-flash-preview', claude: 'claude-sonnet-4-6',
  openai: 'gpt-4o', deepseek: 'deepseek-chat', openai_compatible: '',
}

function getRoleModel(settings: any, role: 'expansion' | 'extraction'): string {
  const p = settings?.provider || 'gemini'
  const prefix = PROVIDER_PREFIX[p]
  if (!prefix) return ''
  return settings?.[`${prefix}_${role}_model`] || settings?.[`${prefix}_model`] || PROVIDER_DEFAULT[p]
}

function getExpansionModel(settings: any): string { return getRoleModel(settings, 'expansion') }
function getExtractionModel(settings: any): string { return getRoleModel(settings, 'extraction') }

const modelDisplay = computed(() => {
  if (expansionModelLabel.value === extractionModelLabel.value) {
    return expansionModelLabel.value
  }
  return `${t('status.expansionModel', { model: expansionModelLabel.value })} | ${t('status.extractionModel', { model: extractionModelLabel.value })}`
})

const currentProject = computed(() =>
  projectStore.currentProjectName || t('status.noProject')
)

const recordCount = computed(() => {
  const n = projectStore.currentProject?.record_count
  if (!n) return ''
  if (n >= 10000) return `${(n / 10000).toFixed(1)}${t('format.wan')}`
  return n.toLocaleString()
})

function updateFromSettings(settings: any) {
  const p = settings?.provider || 'gemini'
  providerLabel.value = getProviderLabel(p)
  const expKey = getExpansionModel(settings)
  const extKey = getExtractionModel(settings)
  expansionModelLabel.value = getModelLabel(p, expKey)
  extractionModelLabel.value = getModelLabel(p, extKey)
}

async function loadSettingsInfo() {
  try {
    const settings = await api.get<any>('/api/settings')
    updateFromSettings(settings)
  } catch {}
}

// 后端就绪后加载模型信息（就绪状态由 backend store 统一轮询）
watch(() => backend.ready, (r) => { if (r) loadSettingsInfo() }, { immediate: true })

onMounted(() => {
  window.addEventListener('settings-updated', loadSettingsInfo)
  onUnmounted(() => window.removeEventListener('settings-updated', loadSettingsInfo))
})
</script>

<style scoped>
.status-bar {
  height: 24px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--sidebar-bg);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  margin-right: 6px;
  flex-shrink: 0;
}
.dot-ok  { background: #48BB78; }
.dot-err { background: #FC8181; }

.status-item { padding: 0 5px; }
.provider-tag { font-weight: 500; opacity: 0.9; }
.model-name { opacity: 0.8; }
.sep { color: var(--border); }
</style>
