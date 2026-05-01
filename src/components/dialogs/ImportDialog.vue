<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="import-dialog">
      <!-- 标题 -->
      <div class="dialog-header">
        <span class="dialog-title">{{ t('import.title') }}</span>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- 分步：Step 1 选文件 -->
      <template v-if="step === 1">
        <div class="dialog-body">
          <!-- 说明 -->
          <p class="import-hint">{{ t('import.hint', { project: projectName }) }}</p>

          <!-- 文件选择 -->
          <div class="field-group">
            <label class="field-label">{{ t('import.selectFile') }}</label>
            <div class="file-drop-zone" :class="{ 'has-file': hasFile }" @click="openFilePicker">
              <template v-if="!hasFile">
                <div class="drop-icon">📂</div>
                <p class="drop-hint">{{ t('import.clickToSelect') }}</p>
                <p class="drop-sub">{{ t('import.supportedFormats') }}</p>
              </template>
              <template v-else>
                <div class="file-info">
                  <span class="file-icon">{{ fileTypeIcon }}</span>
                  <div>
                    <p class="file-name">{{ selectedFileName }}</p>
                    <p class="file-size">{{ formatSize(selectedFileSize) }}</p>
                  </div>
                  <button class="remove-file" @click.stop="clearFile">✕</button>
                </div>
              </template>
            </div>
            <!-- 隐藏的 file input（Web 开发环境备用） -->
            <input
              ref="fileInput"
              type="file"
              style="display:none"
              accept=".csv,.pdf,.docx,.doc,.txt,.epub,.mobi,.azw3"
              @change="onFileSelected"
            />
          </div>

          <!-- 文献类型 -->
          <div class="field-group" v-if="hasFile && !isCsv">
            <label class="field-label">{{ t('import.docType') }}</label>
            <div class="type-grid">
              <button
                v-for="dt in DOC_TYPES"
                :key="dt.value"
                class="type-btn"
                :class="{ active: docType === dt.value }"
                @click="docType = dt.value"
              >
                <span class="type-icon">{{ dt.icon }}</span>
                <span>{{ dt.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn-ghost" @click="$emit('close')">{{ t('common.cancel') }}</button>
          <button
            class="btn-primary"
            :disabled="!hasFile"
            @click="nextStep"
          >
            {{ t('import.nextStep') }}
          </button>
        </div>
      </template>

      <!-- Step 2：填写元数据 -->
      <template v-else-if="step === 2">
        <div class="dialog-body">
          <p class="step-hint">{{ t('import.metaHint') }}</p>

          <!-- CSV 报纸无需元数据 -->
          <template v-if="!isCsv">
            <div class="meta-grid">
              <div class="field-group">
                <label class="field-label">{{ t('import.docTitleLabel') }}</label>
                <input v-model="meta.title" class="input" :placeholder="selectedFileName || ''" />
              </div>

              <template v-if="docType !== 'interview'">
                <div class="field-group">
                  <label class="field-label">{{ t('import.authorLabel') }}</label>
                  <input v-model="meta.author" class="input" :placeholder="t('import.authorPlaceholder')" />
                </div>
                <div class="field-group">
                  <label class="field-label">{{ t('import.pubYearLabel') }}</label>
                  <input v-model="meta.pub_year" class="input" :placeholder="t('import.pubYearPlaceholder')" maxlength="4" />
                </div>
                <div class="field-group" v-if="docType === 'book'">
                  <label class="field-label">{{ t('import.publisherLabel') }}</label>
                  <input v-model="meta.publisher" class="input" :placeholder="t('import.publisherPlaceholder')" />
                </div>
              </template>

              <template v-if="docType === 'interview'">
                <div class="field-group">
                  <label class="field-label">{{ t('import.intervieweeLabel') }}</label>
                  <input v-model="meta.interviewee" class="input" :placeholder="t('import.intervieweePlaceholder')" />
                </div>
                <div class="field-group">
                  <label class="field-label">{{ t('import.interviewDateLabel') }}</label>
                  <input v-model="meta.interview_date" class="input" :placeholder="t('import.interviewDatePlaceholder')" />
                </div>
                <div class="field-group">
                  <label class="field-label">{{ t('import.interviewLocationLabel') }}</label>
                  <input v-model="meta.interview_location" class="input" :placeholder="t('import.interviewLocationPlaceholder')" />
                </div>
              </template>
            </div>
          </template>

          <template v-else>
            <div class="csv-info">
              <p>{{ t('import.csvInfo') }}</p>
              <p>{{ t('import.csvInfoLine2') }}</p>
            </div>
          </template>
        </div>

        <div class="dialog-footer">
          <button class="btn-ghost" @click="step = 1">{{ t('import.prevStep') }}</button>
          <button class="btn-primary" @click="startImport" :disabled="importing">
            {{ importing ? t('import.importing') : t('import.startImport') }}
          </button>
        </div>
      </template>

      <!-- Step 3：导入进度 -->
      <template v-else-if="step === 3">
        <div class="dialog-body">
          <div class="progress-wrap">
            <div class="progress-icon">
              <template v-if="importStatus === 'done'">✅</template>
              <template v-else-if="importStatus === 'error'">❌</template>
              <template v-else>
                <div class="spinner" />
              </template>
            </div>
            <p class="progress-message">{{ progressMessage }}</p>

            <!-- 进度条 -->
            <div v-if="importStatus === 'running'" class="progress-bar-wrap">
              <div class="progress-bar" :style="{ width: progressPct + '%' }" />
            </div>

            <p v-if="importStatus === 'done'" class="done-count">
              {{ t('import.successCount', { count: importedCount.toLocaleString() }) }}
            </p>
            <p v-if="importStatus === 'error'" class="error-msg">
              {{ errorMessage }}
            </p>
          </div>
        </div>

        <div class="dialog-footer">
          <button
            v-if="importStatus === 'done'"
            class="btn-primary w-full"
            @click="handleDone"
          >
            {{ t('common.done') }}
          </button>
          <button
            v-else-if="importStatus === 'error'"
            class="btn-ghost"
            @click="step = 1; importing = false"
          >
            {{ t('common.retry') }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'

const { t } = useI18n()

const props = defineProps<{
  projectName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'imported'): void
}>()

// ── State ──────────────────────────────────────────
const step = ref(1)
// Tauri 环境：存文件系统绝对路径
const selectedFilePath = ref<string>('')
// 仅用于显示（name + size）
const selectedFileName = ref<string>('')
const selectedFileSize = ref<number>(0)
// Web 开发环境备用
const webFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const docType = ref('newspaper')

const meta = ref({
  title: '',
  author: '',
  pub_year: '',
  publisher: '',
  interviewee: '',
  interview_date: '',
  interview_location: '',
})

const importing = ref(false)
const importStatus = ref<'pending' | 'running' | 'done' | 'error'>('pending')
const progressPct = ref(0)
const progressMessage = ref('')
const importedCount = ref(0)
const errorMessage = ref('')

// ── Computed ──────────────────────────────────────
const DOC_TYPES = computed(() => [
  { value: 'newspaper', icon: '📰', label: t('import.docTypeNewspaper') },
  { value: 'book',      icon: '📚', label: t('import.docTypeBook') },
  { value: 'paper',     icon: '📄', label: t('import.docTypePaper') },
  { value: 'interview', icon: '🎙️', label: t('import.docTypeInterview') },
])

const hasFile = computed(() => !!(selectedFilePath.value || webFile.value))

const isCsv = computed(() =>
  selectedFileName.value.toLowerCase().endsWith('.csv')
)

const fileTypeIcon = computed(() => {
  const name = selectedFileName.value.toLowerCase()
  if (name.endsWith('.csv'))  return '📰'
  if (name.endsWith('.pdf'))  return '📄'
  if (name.endsWith('.epub') || name.endsWith('.mobi')) return '📖'
  if (name.endsWith('.docx') || name.endsWith('.doc'))  return '📝'
  return '📄'
})

// ── Methods ────────────────────────────────────────
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

async function openFilePicker() {
  if (isTauri) {
    // Tauri 原生文件选择器：直接返回文件系统路径，无需读取文件内容
    try {
      const { open } = await import('@tauri-apps/plugin-dialog')
      const result = await open({
        multiple: false,
        filters: [{
          name: t('import.fileFilterName'),
          extensions: ['csv', 'pdf', 'docx', 'doc', 'txt', 'epub', 'mobi', 'azw3'],
        }],
      })
      if (result && typeof result === 'string') {
        _applyFilePath(result)
      }
    } catch (e) {
      console.error('Tauri dialog failed, falling back to file input', e)
      fileInput.value?.click()
    }
  } else {
    fileInput.value?.click()
  }
}

function _applyFilePath(path: string) {
  selectedFilePath.value = path
  // 提取文件名（兼容 / 和 \ 路径分隔符）
  const name = path.replace(/\\/g, '/').split('/').pop() || path
  selectedFileName.value = name
  selectedFileSize.value = 0  // Tauri dialog 不直接提供文件大小
  webFile.value = null
  if (isCsv.value) docType.value = 'newspaper'
  meta.value.title = name.replace(/\.[^/.]+$/, '')
}

function onFileSelected(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    webFile.value = file
    selectedFilePath.value = ''
    selectedFileName.value = file.name
    selectedFileSize.value = file.size
    if (isCsv.value) docType.value = 'newspaper'
    meta.value.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

function clearFile() {
  selectedFilePath.value = ''
  selectedFileName.value = ''
  selectedFileSize.value = 0
  webFile.value = null
}

function formatSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function nextStep() {
  if (!hasFile.value) return
  step.value = 2
}

async function startImport() {
  if (!hasFile.value) return
  importing.value = true
  step.value = 3
  importStatus.value = 'running'
  progressMessage.value = t('import.preparing')

  try {
    let filePath: string

    if (selectedFilePath.value) {
      // Tauri 环境：直接使用文件系统路径，无需上传
      filePath = selectedFilePath.value
    } else if (webFile.value) {
      // Web 开发环境备用：上传文件
      filePath = await uploadFileToBackend(webFile.value)
    } else {
      throw new Error(t('import.noFileSelected'))
    }

    // 启动导入任务
    const { task_id } = await api.post<{ task_id: string }>('/api/import/start', {
      project_name: props.projectName,
      file_path: filePath,
      use_shared: true,
      doc_type: isCsv.value ? 'newspaper' : docType.value,
      title: meta.value.title || selectedFileName.value,
      author: meta.value.author,
      pub_year: meta.value.pub_year,
      publisher: meta.value.publisher,
      interviewee: meta.value.interviewee,
      interview_date: meta.value.interview_date,
      interview_location: meta.value.interview_location,
    })

    // 监听进度 SSE
    const es = api.stream(`/api/import/${task_id}/progress`)
    es.onmessage = (event) => {
      const data = JSON.parse(event.data)
      importStatus.value = data.status
      progressPct.value = data.progress || 0
      progressMessage.value = data.message || ''
      importedCount.value = data.imported || 0
      if (data.error) errorMessage.value = data.error
      if (data.status === 'done' || data.status === 'error') {
        es.close()
      }
    }
    es.onerror = () => {
      es.close()
      if (importStatus.value !== 'done') {
        importStatus.value = 'error'
        errorMessage.value = t('import.sseDisconnected')
      }
    }
  } catch (err: any) {
    importStatus.value = 'error'
    errorMessage.value = err.message || t('import.failed')
    progressMessage.value = t('import.failed')
  }
}

/**
 * Web 开发环境备用上传（Tauri 环境不走此路径）。
 * 使用 FileReader + ArrayBuffer 避免 file.arrayBuffer() 兼容性问题。
 */
async function uploadFileToBackend(file: File): Promise<string> {
  const arrayBuffer = await new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as ArrayBuffer)
    reader.onerror = () => reject(new Error(reader.error?.message || t('import.fileReadFailed')))
    reader.readAsArrayBuffer(file)
  })
  const res = await fetch('http://127.0.0.1:8765/api/upload', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-Filename': encodeURIComponent(file.name),
    },
    body: arrayBuffer,
  })
  if (!res.ok) {
    const errText = await res.text().catch(() => '')
    throw new Error(`${t('import.uploadFailed')} (${res.status})${errText ? ': ' + errText : ''}`)
  }
  const data = await res.json()
  return data.path
}

function handleDone() {
  emit('imported')
  emit('close')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.import-dialog {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  width: 520px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.dialog-title {
  font-size: 15px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  color: var(--text-muted);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}
.close-btn:hover { background: var(--hover-bg); }

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.dialog-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.import-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 14px;
  padding: 8px 10px;
  background: var(--sidebar-bg);
  border-radius: var(--radius);
}

/* Field */
.field-group { margin-bottom: 16px; }
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Radio group */
.radio-group { display: flex; flex-direction: column; gap: 6px; }
.radio-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius);
  border: 1.5px solid var(--border);
  cursor: pointer;
  transition: all 150ms;
  font-size: 13px;
}
.radio-item:hover { border-color: var(--accent); background: #f0f7ff; }
.radio-item.selected { border-color: var(--accent); background: #EBF4FF; }
.radio-item em { color: var(--text-muted); font-style: normal; font-size: 12px; }
.radio-dot {
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border);
  flex-shrink: 0;
  transition: all 150ms;
}
.radio-dot.active {
  border-color: var(--accent);
  background: var(--accent);
  box-shadow: inset 0 0 0 2px white;
}

/* File drop zone */
.file-drop-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius-md);
  padding: 28px;
  text-align: center;
  cursor: pointer;
  transition: all 150ms;
}
.file-drop-zone:hover, .file-drop-zone.has-file {
  border-color: var(--accent);
  background: #f7faff;
}
.drop-icon { font-size: 32px; margin-bottom: 8px; }
.drop-hint { font-size: 14px; font-weight: 500; margin: 0 0 4px; color: var(--text); }
.drop-sub { font-size: 12px; color: var(--text-muted); margin: 0; }

.file-info {
  display: flex; align-items: center; gap: 12px;
  text-align: left;
}
.file-icon { font-size: 28px; }
.file-name { font-size: 13px; font-weight: 500; margin: 0 0 2px; }
.file-size { font-size: 11px; color: var(--text-muted); margin: 0; }
.remove-file {
  margin-left: auto;
  background: none; border: none;
  color: var(--text-muted); cursor: pointer;
  font-size: 14px; padding: 4px;
}
.remove-file:hover { color: #e53e3e; }

/* Doc type grid */
.type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.type-btn {
  display: flex; flex-direction: column; align-items: center;
  gap: 4px; padding: 10px 8px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  background: transparent;
  font-size: 12px; cursor: pointer;
  transition: all 150ms; color: var(--text);
}
.type-btn:hover { border-color: var(--accent); background: #f0f7ff; }
.type-btn.active {
  border-color: var(--accent);
  background: #EBF4FF;
  color: var(--accent);
  font-weight: 500;
}
.type-icon { font-size: 20px; }

/* Metadata grid */
.meta-grid { display: flex; flex-direction: column; gap: 0; }
.step-hint { font-size: 12px; color: var(--text-muted); margin: 0 0 16px; }

.csv-info {
  background: var(--sidebar-bg);
  border-radius: var(--radius-md);
  padding: 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-muted);
}

/* Progress */
.progress-wrap {
  display: flex; flex-direction: column;
  align-items: center; text-align: center;
  padding: 20px 0;
  gap: 12px;
}
.progress-icon { font-size: 40px; }
.progress-message { font-size: 14px; color: var(--text); margin: 0; }
.progress-bar-wrap {
  width: 100%;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 300ms ease;
}
.done-count { font-size: 13px; color: var(--text-muted); margin: 0; }
.done-count b { color: var(--accent); }
.error-msg { font-size: 12px; color: #e53e3e; margin: 0; }

/* Spinner */
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.w-full { width: 100%; }
</style>
