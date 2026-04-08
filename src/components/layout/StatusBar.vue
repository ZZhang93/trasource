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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'

const { t } = useI18n()

const projectStore = useProjectStore()
const backendStatusKey = ref('status.connecting')
const backendStatus = computed(() => t(backendStatusKey.value))
const backendOk = ref(false)
const providerLabel = ref('Gemini')
const expansionModelLabel = ref('')
const extractionModelLabel = ref('')

function getProviderLabel(p: string): string {
  const STATIC: Record<string, string> = {
    gemini: 'Gemini',
    claude: 'Claude',
    openai: 'ChatGPT',
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
  }
  return SHORT[modelId] || modelId
}

function getExpansionModel(settings: any): string {
  const p = settings?.provider || 'gemini'
  if (p === 'gemini') return settings?.gemini_expansion_model || 'gemini-3-flash-preview'
  if (p === 'claude') return settings?.claude_expansion_model || 'claude-sonnet-4-6'
  if (p === 'openai') return settings?.openai_expansion_model || 'gpt-4o'
  if (p === 'openai_compatible') return settings?.local_expansion_model || settings?.local_model || ''
  return ''
}

function getExtractionModel(settings: any): string {
  const p = settings?.provider || 'gemini'
  if (p === 'gemini') return settings?.gemini_extraction_model || 'gemini-3-flash-preview'
  if (p === 'claude') return settings?.claude_extraction_model || 'claude-sonnet-4-6'
  if (p === 'openai') return settings?.openai_extraction_model || 'gpt-4o'
  if (p === 'openai_compatible') return settings?.local_extraction_model || settings?.local_model || ''
  return ''
}

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

onMounted(() => {
  let attempts = 0
  const MAX = 30

  const check = async () => {
    attempts++
    try {
      await api.get('/api/health')
      backendStatusKey.value = 'status.ready'
      backendOk.value = true
      const settings = await api.get<any>('/api/settings')
      updateFromSettings(settings)
    } catch {
      if (attempts < MAX) {
        backendStatusKey.value = 'status.starting'
        backendOk.value = false
        setTimeout(check, 3000)
      } else {
        backendStatusKey.value = 'status.offline'
        backendOk.value = false
      }
    }
  }

  check()

  const onSettingsUpdated = async () => {
    try {
      const settings = await api.get<any>('/api/settings')
      updateFromSettings(settings)
    } catch {}
  }
  window.addEventListener('settings-updated', onSettingsUpdated)
  onUnmounted(() => window.removeEventListener('settings-updated', onSettingsUpdated))
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
