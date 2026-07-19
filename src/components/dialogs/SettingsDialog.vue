<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="settings-dialog">
      <!-- 标题 -->
      <div class="dialog-header">
        <span class="dialog-title">{{ t('settings.title') }}</span>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- 标签页 -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <!-- 内容 -->
      <div class="tab-body">

        <!-- ── AI 服务 ── -->
        <div v-if="activeTab === 'api'">
          <!-- Provider 选择 -->
          <div class="form-group">
            <label>{{ t('settings.providerLabel') }}</label>
            <div class="provider-selector">
              <button
                v-for="p in providers"
                :key="p.value"
                class="provider-btn"
                :class="{ active: form.provider === p.value }"
                @click="form.provider = p.value"
              >{{ providerLabel(p.value) }}</button>
            </div>
          </div>

          <!-- Gemini -->
          <template v-if="form.provider === 'gemini'">
            <div class="form-group">
              <label>{{ t('settings.geminiApiKey') }}</label>
              <div class="input-with-btn">
                <input
                  v-model="form.gemini_api_key"
                  :type="showKey ? 'text' : 'password'"
                  class="form-input"
                  placeholder="AIzaSy…"
                />
                <button class="inline-btn" @click="showKey = !showKey">
                  {{ showKey ? t('settings.hideKey') : t('settings.showKey') }}
                </button>
              </div>
              <p class="hint muted">{{ t('settings.apiKeyHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ t('settings.expansionModelLabel') }}</label>
              <select v-model="form.gemini_expansion_model" class="form-select">
                <option v-for="m in modelLists.gemini" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('settings.extractionModelLabel') }}</label>
              <select v-model="form.gemini_extraction_model" class="form-select">
                <option v-for="m in modelLists.gemini" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
          </template>

          <!-- Claude -->
          <template v-if="form.provider === 'claude'">
            <div class="form-group">
              <label>{{ t('settings.claudeApiKey') }}</label>
              <div class="input-with-btn">
                <input
                  v-model="form.claude_api_key"
                  :type="showKey ? 'text' : 'password'"
                  class="form-input"
                  placeholder="sk-ant-…"
                />
                <button class="inline-btn" @click="showKey = !showKey">
                  {{ showKey ? t('settings.hideKey') : t('settings.showKey') }}
                </button>
              </div>
              <p class="hint muted">{{ t('settings.apiKeyLocalHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ t('settings.expansionModelLabel') }}</label>
              <select v-model="form.claude_expansion_model" class="form-select">
                <option v-for="m in modelLists.claude" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('settings.extractionModelLabel') }}</label>
              <select v-model="form.claude_extraction_model" class="form-select">
                <option v-for="m in modelLists.claude" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
          </template>

          <!-- OpenAI (ChatGPT) -->
          <template v-if="form.provider === 'openai'">
            <div class="form-group">
              <label>{{ t('settings.openaiApiKey') }}</label>
              <div class="input-with-btn">
                <input
                  v-model="form.openai_api_key"
                  :type="showKey ? 'text' : 'password'"
                  class="form-input"
                  placeholder="sk-…"
                />
                <button class="inline-btn" @click="showKey = !showKey">
                  {{ showKey ? t('settings.hideKey') : t('settings.showKey') }}
                </button>
              </div>
              <p class="hint muted">{{ t('settings.apiKeyLocalHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ t('settings.expansionModelLabel') }}</label>
              <select v-model="form.openai_expansion_model" class="form-select">
                <option v-for="m in modelLists.openai" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('settings.extractionModelLabel') }}</label>
              <select v-model="form.openai_extraction_model" class="form-select">
                <option v-for="m in modelLists.openai" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
          </template>

          <!-- DeepSeek -->
          <template v-if="form.provider === 'deepseek'">
            <div class="form-group">
              <label>{{ t('settings.deepseekApiKey') }}</label>
              <div class="input-with-btn">
                <input
                  v-model="form.deepseek_api_key"
                  :type="showKey ? 'text' : 'password'"
                  class="form-input"
                  placeholder="sk-…"
                />
                <button class="inline-btn" @click="showKey = !showKey">
                  {{ showKey ? t('settings.hideKey') : t('settings.showKey') }}
                </button>
              </div>
              <p class="hint muted">{{ t('settings.apiKeyLocalHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ t('settings.expansionModelLabel') }}</label>
              <select v-model="form.deepseek_expansion_model" class="form-select">
                <option v-for="m in modelLists.deepseek" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('settings.extractionModelLabel') }}</label>
              <select v-model="form.deepseek_extraction_model" class="form-select">
                <option v-for="m in modelLists.deepseek" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
          </template>

          <!-- Kimi (Moonshot AI) -->
          <template v-if="form.provider === 'kimi'">
            <div class="form-group">
              <label>{{ t('settings.kimiApiKey') }}</label>
              <div class="input-with-btn">
                <input
                  v-model="form.kimi_api_key"
                  :type="showKey ? 'text' : 'password'"
                  class="form-input"
                  placeholder="sk-…"
                />
                <button class="inline-btn" @click="showKey = !showKey">
                  {{ showKey ? t('settings.hideKey') : t('settings.showKey') }}
                </button>
              </div>
              <p class="hint muted">{{ t('settings.apiKeyLocalHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ t('settings.expansionModelLabel') }}</label>
              <select v-model="form.kimi_expansion_model" class="form-select">
                <option v-for="m in modelLists.kimi" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('settings.extractionModelLabel') }}</label>
              <select v-model="form.kimi_extraction_model" class="form-select">
                <option v-for="m in modelLists.kimi" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
          </template>

          <!-- 本地模型 -->
          <template v-if="form.provider === 'openai_compatible'">
            <div class="form-group">
              <label>{{ t('settings.localBaseUrl') }}</label>
              <input
                v-model="form.local_base_url"
                class="form-input"
                placeholder="http://localhost:11434/v1"
              />
              <p class="hint muted">{{ t('settings.localBaseUrlHint') }}</p>
            </div>
            <div class="form-group">
              <label>{{ t('settings.localApiKeyLabel') }}</label>
              <input
                v-model="form.local_api_key"
                :type="showKey ? 'text' : 'password'"
                class="form-input"
                :placeholder="t('settings.localApiKeyPlaceholder')"
              />
            </div>
            <div class="form-group">
              <label>{{ t('settings.expansionModelLabel') }}</label>
              <input
                v-model="form.local_expansion_model"
                class="form-input"
                list="local-model-options"
                :placeholder="t('settings.localModelPlaceholder')"
              />
            </div>
            <div class="form-group">
              <label>{{ t('settings.extractionModelLabel') }}</label>
              <input
                v-model="form.local_extraction_model"
                class="form-input"
                list="local-model-options"
                :placeholder="t('settings.localModelPlaceholder')"
              />
            </div>
            <datalist id="local-model-options">
              <option v-for="m in modelLists.openai_compatible" :key="m.value" :value="m.value" />
            </datalist>
          </template>

          <!-- 获取最新模型 + 测试连接 -->
          <div class="form-group action-row">
            <button
              class="btn-test"
              :disabled="fetchingModels"
              @click="fetchModels(true)"
            >{{ fetchingModels ? t('settings.fetchingModels') : t('settings.fetchModels') }}</button>
            <button
              class="btn-test"
              :disabled="testing"
              @click="testConnection"
            >{{ testing ? t('settings.testing') : t('settings.testConnection') }}</button>
          </div>
          <p class="hint muted fetch-hint">{{ t('settings.fetchModelsHint') }}</p>
          <p v-if="testResult" class="hint" :class="testResult.success ? 'ok' : 'err'">
            {{ testResult.message }}
          </p>

          <div class="form-group">
            <label>{{ t('settings.proxyLabel') }}</label>
            <input
              v-model="form.proxy_url"
              class="form-input"
              placeholder="https://your-proxy.example.com"
            />
            <p class="hint muted">{{ t('settings.proxyHint') }}</p>
          </div>
        </div>

        <!-- ── 检索设置 ── -->
        <div v-if="activeTab === 'search'">
          <div class="form-group">
            <label>{{ t('settings.topKLabel') }}</label>
            <div class="range-row">
              <input
                type="range" min="10" max="200" step="10"
                v-model.number="form.top_k"
                style="flex:1;accent-color:var(--accent)"
              />
              <span class="range-val">{{ t('settings.topKUnit', { count: form.top_k }) }}</span>
            </div>
            <p class="hint muted">{{ t('settings.topKHint') }}</p>
          </div>
        </div>

        <!-- ── 自定义提示词 ── -->
        <div v-if="activeTab === 'prompt'" class="prompt-tab">
          <div class="form-group">
            <div class="prompt-label-row">
              <label>{{ t('settings.expansionPromptLabel') }}</label>
              <button class="btn-ghost btn-sm" @click="form.expansion_prompt_override = defaultPrompts.expansion">
                {{ t('settings.restoreDefault') }}
              </button>
            </div>
            <textarea
              v-model="form.expansion_prompt_override"
              class="form-textarea"
              :placeholder="defaultPrompts.expansion || t('common.loading')"
              rows="8"
              spellcheck="false"
            />
            <p class="hint muted">
              {{ t('settings.expansionPromptHint') }}
            </p>
          </div>

          <div class="prompt-divider" />

          <div class="form-group">
            <div class="prompt-label-row">
              <label>{{ t('settings.extractionPromptLabel') }}</label>
              <button class="btn-ghost btn-sm" @click="form.system_prompt_override = defaultPrompts.extraction">
                {{ t('settings.restoreDefault') }}
              </button>
            </div>
            <textarea
              v-model="form.system_prompt_override"
              class="form-textarea"
              :placeholder="defaultPrompts.extraction || t('common.loading')"
              rows="8"
              spellcheck="false"
            />
            <p class="hint muted">
              {{ t('settings.extractionPromptHint') }}
            </p>
          </div>
        </div>

        <!-- ── 关于 ── -->
        <div v-if="activeTab === 'about'" class="about-tab">
          <div class="about-logo">📜</div>
          <h2>{{ t('settings.aboutTitle') }}</h2>
          <p class="version">{{ t('settings.aboutVersion', { version: appVersion }) }}</p>
          <p class="about-desc">
            {{ t('settings.aboutDesc') }}<br>
            {{ t('settings.aboutDescLine2') }}
          </p>
          <div class="about-links">
            <div class="about-row">
              <span class="about-label">{{ t('settings.aboutFrontend') }}</span>
              <span>Vue 3 + TailwindCSS</span>
            </div>
            <div class="about-row">
              <span class="about-label">{{ t('settings.aboutDesktop') }}</span>
              <span>Tauri v2</span>
            </div>
            <div class="about-row">
              <span class="about-label">{{ t('settings.aboutBackend') }}</span>
              <span>Python FastAPI</span>
            </div>
            <div class="about-row">
              <span class="about-label">{{ t('settings.aboutDatabase') }}</span>
              <span>DuckDB + SQLite</span>
            </div>
            <div class="about-row">
              <span class="about-label">{{ t('settings.aboutAIModel') }}</span>
              <span>{{ t('settings.aboutAIModelValue') }}</span>
            </div>
          </div>
        </div>

      </div>

      <!-- 底部 -->
      <div class="dialog-footer">
        <button class="btn-ghost" @click="$emit('close')">{{ t('common.cancel') }}</button>
        <button class="btn-primary" @click="save" :disabled="saving">
          {{ saving ? t('settings.saving') : t('settings.saveSettings') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useI18n } from '@/i18n'

const { t, locale, setLocale } = useI18n()
const ui = useUiStore()

// 构建时从 package.json 注入
const appVersion = __APP_VERSION__

defineEmits<{ close: [] }>()

const currentLocale = ref(locale.value)

function onLocaleChange() {
  setLocale(currentLocale.value)
}

const providerLabelMap: Record<string, string> = {
  gemini: 'settings.providerGemini',
  claude: 'settings.providerClaude',
  openai: 'settings.providerOpenAI',
  deepseek: 'settings.providerDeepSeek',
  kimi: 'settings.providerKimi',
  openai_compatible: 'settings.providerLocal',
}

function providerLabel(value: string): string {
  return providerLabelMap[value] ? t(providerLabelMap[value]) : value
}

const tabs = computed(() => [
  { id: 'api', label: t('settings.tabAI') },
  { id: 'search', label: t('settings.tabSearch') },
  { id: 'prompt', label: t('settings.tabPrompt') },
  { id: 'about', label: t('settings.tabAbout') },
])
const activeTab = ref('api')

const form = reactive({
  provider: 'gemini',

  gemini_api_key: '',
  gemini_model: 'gemini-3-flash-preview',
  gemini_expansion_model: 'gemini-3-flash-preview',
  gemini_extraction_model: 'gemini-3-flash-preview',

  claude_api_key: '',
  claude_model: 'claude-sonnet-4-6',
  claude_expansion_model: 'claude-haiku-4-5-20251001',
  claude_extraction_model: 'claude-sonnet-4-6',

  openai_api_key: '',
  openai_model: 'gpt-4o',
  openai_expansion_model: 'gpt-4o-mini',
  openai_extraction_model: 'gpt-4o',

  deepseek_api_key: '',
  deepseek_model: 'deepseek-chat',
  deepseek_expansion_model: 'deepseek-chat',
  deepseek_extraction_model: 'deepseek-chat',

  kimi_api_key: '',
  kimi_model: 'kimi-latest',
  kimi_expansion_model: 'kimi-latest',
  kimi_extraction_model: 'kimi-latest',

  local_base_url: 'http://localhost:11434/v1',
  local_api_key: '',
  local_model: '',
  local_expansion_model: '',
  local_extraction_model: '',

  proxy_url: '',
  top_k: 50,
  system_prompt_override: '',
  expansion_prompt_override: '',
})

const defaultPrompts = reactive({
  extraction: '',
  expansion: '',
})

interface ModelOption {
  label: string
  value: string
}

const providers = ref<{ label: string; value: string }[]>([
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'claude', label: 'Claude (Anthropic)' },
  { value: 'openai', label: 'ChatGPT (OpenAI)' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'kimi', label: 'Kimi (Moonshot AI)' },
  { value: 'openai_compatible', label: '本地模型 (Ollama / vLLM)' },
])
const modelLists = reactive<Record<string, ModelOption[]>>({
  gemini: [],
  claude: [],
  openai: [],
  deepseek: [],
  kimi: [],
  openai_compatible: [],
})
const showKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const fetchingModels = ref(false)

// ── 在线模型列表：localStorage 缓存 + 打开时自动拉取 ──
const MODELS_CACHE_KEY = 'trasource_models_cache_v1'
const savedKeyMask = reactive<Record<string, string>>({})   // provider → masked key（判断是否已配置）
const autoFetched = new Set<string>()                       // 本次会话已自动拉取过的 provider

const KEY_FIELD: Record<string, string> = {
  gemini: 'gemini_api_key',
  claude: 'claude_api_key',
  openai: 'openai_api_key',
  deepseek: 'deepseek_api_key',
  kimi: 'kimi_api_key',
  openai_compatible: 'local_api_key',
}

function loadCachedModels() {
  try {
    const cache = JSON.parse(localStorage.getItem(MODELS_CACHE_KEY) || '{}')
    for (const [p, entry] of Object.entries<any>(cache)) {
      if (entry?.models?.length && p in modelLists) {
        modelLists[p] = entry.models
      }
    }
  } catch {}
}

function cacheModels(provider: string, models: ModelOption[]) {
  try {
    const cache = JSON.parse(localStorage.getItem(MODELS_CACHE_KEY) || '{}')
    cache[provider] = { models, at: Date.now() }
    localStorage.setItem(MODELS_CACHE_KEY, JSON.stringify(cache))
  } catch {}
}

// 应用拉取结果：当前已选中的模型若不在新列表里，保留在列表顶部（不打断用户已保存的选择）
function applyFetchedModels(provider: string, models: ModelOption[]) {
  const selected = [
    (form as any)[`${provider === 'openai_compatible' ? 'local' : provider}_expansion_model`],
    (form as any)[`${provider === 'openai_compatible' ? 'local' : provider}_extraction_model`],
  ].filter(Boolean)
  const values = new Set(models.map(m => m.value))
  const keep = selected.filter(v => !values.has(v)).map(v => ({ label: v, value: v }))
  modelLists[provider] = [...keep, ...models]
}

async function fetchModels(manual = false) {
  const p = form.provider
  fetchingModels.value = manual
  try {
    const payload: any = { provider: p, api_key: (form as any)[KEY_FIELD[p]] || '' }
    if (p === 'openai_compatible') payload.base_url = form.local_base_url
    const res = await api.post<any>('/api/settings/list-models', payload)
    if (res.success && res.models?.length) {
      applyFetchedModels(p, res.models)
      cacheModels(p, res.models)
      if (manual) ui.toast(t('toast.modelsUpdated', { count: res.models.length }), 'success')
    } else if (manual) {
      ui.toast(res.message || t('toast.modelsFetchFailed'), 'error')
    }
  } catch {
    if (manual) ui.toast(t('toast.modelsFetchFailed'), 'error')
  } finally {
    fetchingModels.value = false
  }
}

// 切到某个 provider 时，若已配置 key 且本次会话没拉取过，静默自动拉取一次
function autoFetchIfConfigured(p: string) {
  if (autoFetched.has(p)) return
  const hasKey = !!savedKeyMask[p] || !!(form as any)[KEY_FIELD[p]] || p === 'openai_compatible'
  if (!hasKey) return
  autoFetched.add(p)
  fetchModels(false)
}

watch(() => form.provider, (p) => autoFetchIfConfigured(p))

onMounted(async () => {
  try {
    const [settings, modelsData, prompts] = await Promise.all([
      api.get<any>('/api/settings'),
      api.get<any>('/api/settings/models'),
      api.get<any>('/api/settings/default-prompts'),
    ])

    // Provider 列表
    providers.value = modelsData.providers || [
      { value: 'gemini', label: 'Google Gemini' },
      { value: 'claude', label: 'Claude (Anthropic)' },
      { value: 'openai', label: 'ChatGPT (OpenAI)' },
      { value: 'openai_compatible', label: '本地模型' },
    ]

    // 各家模型列表（内置默认 → 本地缓存覆盖 → 自动在线拉取）
    modelLists.gemini = modelsData.gemini || []
    modelLists.claude = modelsData.claude || []
    modelLists.openai = modelsData.openai || []
    modelLists.deepseek = modelsData.deepseek || []
    modelLists.kimi = modelsData.kimi || []
    loadCachedModels()

    // 填充表单
    form.provider = settings.provider || 'gemini'

    form.gemini_expansion_model = settings.gemini_expansion_model || 'gemini-3-flash-preview'
    form.gemini_extraction_model = settings.gemini_extraction_model || 'gemini-3-flash-preview'

    form.claude_expansion_model = settings.claude_expansion_model || 'claude-haiku-4-5-20251001'
    form.claude_extraction_model = settings.claude_extraction_model || 'claude-sonnet-4-6'

    form.openai_expansion_model = settings.openai_expansion_model || 'gpt-4o-mini'
    form.openai_extraction_model = settings.openai_extraction_model || 'gpt-4o'

    form.deepseek_expansion_model = settings.deepseek_expansion_model || 'deepseek-chat'
    form.deepseek_extraction_model = settings.deepseek_extraction_model || 'deepseek-chat'

    form.kimi_expansion_model = settings.kimi_expansion_model || 'kimi-latest'
    form.kimi_extraction_model = settings.kimi_extraction_model || 'kimi-latest'

    // 记录各家是否已配置 key（决定是否自动拉取模型列表）
    savedKeyMask.gemini = settings.gemini_api_key_masked || ''
    savedKeyMask.claude = settings.claude_api_key_masked || ''
    savedKeyMask.openai = settings.openai_api_key_masked || ''
    savedKeyMask.deepseek = settings.deepseek_api_key_masked || ''
    savedKeyMask.kimi = settings.kimi_api_key_masked || ''
    savedKeyMask.openai_compatible = settings.local_api_key_masked || ''

    form.local_base_url = settings.local_base_url || 'http://localhost:11434/v1'
    form.local_expansion_model = settings.local_expansion_model || ''
    form.local_extraction_model = settings.local_extraction_model || ''

    form.proxy_url = settings.proxy_url || ''
    form.top_k = settings.top_k || 50

    defaultPrompts.extraction = prompts.extraction_prompt || ''
    defaultPrompts.expansion = prompts.expansion_prompt || ''
    form.system_prompt_override = settings.system_prompt_override || defaultPrompts.extraction
    form.expansion_prompt_override = settings.expansion_prompt_override || defaultPrompts.expansion

    // 打开设置时，为当前 provider 静默拉取一次最新模型列表
    autoFetchIfConfigured(form.provider)
  } catch (e) {
    console.error('Failed to load settings:', e)
  }
})

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const payload: any = { provider: form.provider }
    if (form.provider === 'gemini') {
      payload.gemini_api_key = form.gemini_api_key
      payload.model = form.gemini_extraction_model
    } else if (form.provider === 'claude') {
      payload.claude_api_key = form.claude_api_key
      payload.model = form.claude_extraction_model
    } else if (form.provider === 'openai') {
      payload.openai_api_key = form.openai_api_key
      payload.model = form.openai_extraction_model
    } else if (form.provider === 'deepseek') {
      payload.deepseek_api_key = form.deepseek_api_key
      payload.model = form.deepseek_extraction_model
    } else if (form.provider === 'kimi') {
      payload.kimi_api_key = form.kimi_api_key
      payload.model = form.kimi_extraction_model
    } else if (form.provider === 'openai_compatible') {
      payload.local_base_url = form.local_base_url
      payload.local_api_key = form.local_api_key
      payload.model = form.local_extraction_model
    }
    const result = await api.post<any>('/api/settings/test-connection', payload)
    testResult.value = result
  } catch {
    testResult.value = { success: false, message: t('settings.testFailed') }
  } finally {
    testing.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await api.put('/api/settings', {
      provider: form.provider,

      gemini_api_key: form.gemini_api_key.trim() || undefined,
      gemini_expansion_model: form.gemini_expansion_model,
      gemini_extraction_model: form.gemini_extraction_model,

      claude_api_key: form.claude_api_key.trim() || undefined,
      claude_expansion_model: form.claude_expansion_model,
      claude_extraction_model: form.claude_extraction_model,

      openai_api_key: form.openai_api_key.trim() || undefined,
      openai_expansion_model: form.openai_expansion_model,
      openai_extraction_model: form.openai_extraction_model,

      deepseek_api_key: form.deepseek_api_key.trim() || undefined,
      deepseek_expansion_model: form.deepseek_expansion_model,
      deepseek_extraction_model: form.deepseek_extraction_model,

      kimi_api_key: form.kimi_api_key.trim() || undefined,
      kimi_expansion_model: form.kimi_expansion_model,
      kimi_extraction_model: form.kimi_extraction_model,

      local_base_url: form.local_base_url.trim(),
      local_api_key: form.local_api_key.trim() || undefined,
      local_expansion_model: form.local_expansion_model.trim(),
      local_extraction_model: form.local_extraction_model.trim(),

      proxy_url: form.proxy_url.trim(),
      top_k: form.top_k,
      system_prompt_override: form.system_prompt_override,
      expansion_prompt_override: form.expansion_prompt_override,
    })
    window.dispatchEvent(new CustomEvent('settings-updated'))
    setTimeout(() => { saving.value = false }, 500)
  } catch (e) {
    console.error('Save failed:', e)
    saving.value = false
  }
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 2000;
}

.settings-dialog {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 580px;
  max-width: calc(100vw - 48px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.dialog-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.header-right {
  display: flex; align-items: center; gap: 8px;
}

.locale-select {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2px 6px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg);
  cursor: pointer;
  outline: none;
}
.locale-select:hover { border-color: var(--accent); color: var(--text); }

.close-btn {
  background: none; border: none; cursor: pointer;
  font-size: 14px; color: var(--text-muted);
  padding: 2px 6px; border-radius: 4px;
  transition: all 150ms;
}
.close-btn:hover { background: var(--hover-bg); color: var(--text); }

/* 标签栏 */
.tab-bar {
  display: flex;
  gap: 2px;
  padding: 8px 12px 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.tab {
  padding: 6px 12px;
  border: none; background: none;
  font-size: 12px; color: var(--text-muted);
  cursor: pointer; border-radius: var(--radius) var(--radius) 0 0;
  transition: all 150ms;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tab:hover { color: var(--text); background: var(--hover-bg); }
.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 500;
}

/* 内容区 */
.tab-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

/* Provider 选择器 */
.provider-selector {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.provider-btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg);
  cursor: pointer;
  transition: all 150ms;
}
.provider-btn:hover {
  border-color: var(--text-muted);
  color: var(--text);
}
.provider-btn.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(35, 131, 226, 0.06);
  font-weight: 500;
}

/* 表单 */
.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 10px;
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms;
}
.form-input:focus { border-color: var(--accent); }

.form-select {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 10px;
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  outline: none;
  cursor: pointer;
}

.form-textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 10px;
  font-size: 12.5px;
  font-family: 'SF Mono', 'JetBrains Mono', monospace;
  color: var(--text);
  background: var(--bg);
  outline: none;
  resize: vertical;
  line-height: 1.6;
  box-sizing: border-box;
}
.form-textarea:focus { border-color: var(--accent); }

.input-with-btn {
  display: flex; gap: 6px;
}
.input-with-btn .form-input { flex: 1; }

.inline-btn {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg);
  cursor: pointer; white-space: nowrap;
  transition: all 150ms;
}
.inline-btn:hover { border-color: var(--text-muted); color: var(--text); }

.btn-test {
  border: 1px solid var(--accent);
  border-radius: var(--radius);
  padding: 6px 16px;
  font-size: 12px;
  color: var(--accent);
  background: var(--bg);
  cursor: pointer;
  transition: all 150ms;
}
.btn-test:hover { background: rgba(35, 131, 226, 0.06); }
.btn-test:disabled { opacity: 0.5; cursor: not-allowed; }
.action-row { display: flex; gap: 8px; margin-bottom: 4px; }
.fetch-hint { margin: 0 0 12px; }

.range-row {
  display: flex; align-items: center; gap: 10px;
}
.range-val {
  font-size: 12px; color: var(--text);
  min-width: 40px; text-align: right;
}

.hint {
  font-size: 11px;
  margin: 5px 0 0;
}
.hint.muted { color: var(--text-muted); }
.hint.ok { color: #38A169; }
.hint.err { color: #e53e3e; }

/* 提示词 */
.prompt-tab .form-group { margin-bottom: 14px; }
.prompt-label-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
}
.prompt-label-row label { margin-bottom: 0; }
.btn-sm { font-size: 11px; padding: 2px 8px; }
.prompt-divider {
  height: 1px; background: var(--border); margin: 6px 0 14px;
}

/* 关于 */
.about-tab {
  text-align: center;
  padding: 12px 0;
}
.about-logo { font-size: 48px; margin-bottom: 10px; }
.about-tab h2 { font-size: 18px; font-weight: 700; margin: 0 0 4px; }
.version { font-size: 12px; color: var(--text-muted); margin: 0 0 12px; }
.about-desc {
  font-size: 13px; color: var(--text-muted);
  line-height: 1.7; margin-bottom: 20px;
}
.about-links {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  text-align: left;
}
.about-row {
  display: flex; justify-content: space-between;
  padding: 7px 14px; font-size: 12px;
  border-bottom: 1px solid var(--border);
}
.about-row:last-child { border-bottom: none; }
.about-label { color: var(--text-muted); }

/* 底部 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
</style>
