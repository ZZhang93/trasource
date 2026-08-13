<template>
  <div class="overlay" @click.self="$emit('close')">
    <div
      ref="dialogEl"
      class="detail-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      :aria-busy="loadingFull"
      tabindex="-1"
      @keydown="handleDialogKeydown"
    >
      <!-- 标题栏 -->
      <div class="dialog-header">
        <div class="header-left">
          <span class="doc-type-badge">{{ docTypeLabel }}</span>
          <span :id="titleId" class="source-name">{{ record.source_file }}</span>
        </div>
        <button
          ref="closeButtonEl"
          class="close-btn"
          :aria-label="t('common.close')"
          @click="$emit('close')"
        >✕</button>
      </div>

      <!-- 元数据行 -->
      <div class="meta-row">
        <span v-if="record.date || record.year" class="meta-tag">
          {{ record.date || record.year }}
        </span>
        <span v-if="record.author" class="meta-tag">{{ record.author }}</span>
        <span v-if="record.title && record.title !== record.source_file" class="meta-tag">
          {{ record.title }}
        </span>
        <span v-if="record.publisher" class="meta-tag">{{ record.publisher }}</span>
        <span v-if="record.pub_year" class="meta-tag">{{ t('detail.year', { year: record.pub_year }) }}</span>
        <span v-if="record.page || record.page_num" class="meta-tag">
          {{ t('detail.page', { page: record.page || record.page_num }) }}
        </span>
        <span v-if="record.chapter" class="meta-tag">{{ record.chapter }}</span>
        <span v-if="record.section" class="meta-tag">{{ record.section }}</span>
        <span v-if="record.interviewee" class="meta-tag">{{ record.interviewee }}</span>
        <span v-if="record.interview_date" class="meta-tag">{{ record.interview_date }}</span>
        <span v-if="record.interview_location" class="meta-tag">{{ record.interview_location }}</span>
        <span v-if="record.relevance_score" class="meta-tag score-tag">
          {{ t('detail.relevanceScore', { score: record.relevance_score }) }}
        </span>
      </div>

      <!-- 正文 -->
      <div class="content-area">
        <div class="content-text">{{ fullContent }}</div>
        <p v-if="loadingFull" class="loading-full" role="status">{{ t('detail.loadingFull') }}</p>
        <div v-else-if="loadError" class="load-error" role="alert">
          <span>{{ t('detail.loadFullFailed') }}</span>
          <button ref="retryButtonEl" class="retry-full" @click="loadFullContent">{{ t('common.retry') }}</button>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="dialog-footer">
        <button class="btn-ghost" @click="copyContent" :disabled="loadingFull || loadError">
          {{ copied ? t('detail.copied') : t('detail.copyOriginal') }}
        </button>
        <button class="btn-primary" @click="emitCreateNote" :disabled="loadingFull || loadError">
          {{ t('detail.createNote') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import type { SearchRecord } from '@/stores/search'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useSearchStore } from '@/stores/search'

const { t } = useI18n()
const projectStore = useProjectStore()
const searchStore = useSearchStore()

const props = defineProps<{ record: SearchRecord }>()
const emit = defineEmits<{
  close: []
  'create-note': [record: SearchRecord]
}>()

const copied = ref(false)
const dialogEl = ref<HTMLElement | null>(null)
const closeButtonEl = ref<HTMLButtonElement | null>(null)
const retryButtonEl = ref<HTMLButtonElement | null>(null)
const titleId = `record-detail-title-${props.record.id}`
let returnFocus: HTMLElement | null = null
// 列表记录只带预览，打开详情时按 id 拉全文
const fullContent = ref(props.record.content)
const loadingFull = ref(false)
const loadError = ref(false)

function focusableElements(): HTMLElement[] {
  if (!dialogEl.value) return []
  return Array.from(dialogEl.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )).filter(element => !element.hasAttribute('hidden'))
}

function handleDialogKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return

  const focusable = focusableElements()
  if (!focusable.length) {
    event.preventDefault()
    dialogEl.value?.focus()
    return
  }
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  const active = document.activeElement
  if (event.shiftKey && (active === first || active === dialogEl.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && (active === last || active === dialogEl.value)) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  void nextTick(() => closeButtonEl.value?.focus())
  void loadFullContent()
})

onUnmounted(() => {
  const target = returnFocus
  void nextTick(() => {
    if (target?.isConnected) target.focus()
  })
})

async function loadFullContent() {
  if (!props.record.content_truncated) return
  const retryHadFocus = document.activeElement === retryButtonEl.value
  loadError.value = false
  loadingFull.value = true
  if (retryHadFocus) void nextTick(() => closeButtonEl.value?.focus())
  try {
    const params = new URLSearchParams()
    if (projectStore.currentProjectName) params.set('project_name', projectStore.currentProjectName)
    // 只有实际进入 AI context 的记录才使用 search_id 约束；原始结果列表中的
    // 其他记录仍以 project_name 做访问控制，否则会被后端正确地拒绝为越界。
    if (searchStore.searchId && searchStore.contextRecordIds.includes(props.record.id)) {
      params.set('search_id', searchStore.searchId)
    }
    const suffix = params.size ? `?${params.toString()}` : ''
    const full = await api.get<SearchRecord>(`/api/search/record/${props.record.id}${suffix}`)
    fullContent.value = full.content
  } catch {
    // 保留预览内容，但明确告诉用户它不是完整原文。
    loadError.value = true
  } finally {
    loadingFull.value = false
  }
}

function emitCreateNote() {
  emit('create-note', { ...props.record, content: fullContent.value, content_truncated: false })
}

const docTypeLabel = computed(() => {
  const map: Record<string, string> = {
    newspaper: t('detail.newspaper'),
    book: t('detail.book'),
    paper: t('detail.paper'),
    interview: t('detail.interview'),
  }
  return map[props.record.doc_type] || props.record.doc_type || t('detail.literature')
})

async function copyContent() {
  try {
    const meta = [
      props.record.source_file,
      props.record.date || props.record.year,
      props.record.author,
      props.record.title !== props.record.source_file ? props.record.title : '',
    ].filter(Boolean).join(' / ')
    await navigator.clipboard.writeText(`${fullContent.value}\n\n——${meta}`)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0;
  background: rgba(23,24,28,0.28);
  backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center;
  z-index: 2000;
  padding: 24px;
}

.detail-dialog {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 680px;
  max-width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.doc-type-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--hover-bg);
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}

.source-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-muted);
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
  transition: all 150ms;
}
.close-btn:hover { background: var(--hover-bg); color: var(--text); }

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.meta-tag {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--hover-bg);
  padding: 2px 7px;
  border-radius: 4px;
}

.score-tag {
  color: var(--accent);
  background: var(--accent-soft);
}

.loading-full {
  font-size: 12px;
  color: var(--text-muted);
  margin: 10px 0 0;
}

.load-error {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  margin-top: 14px; padding: 10px 12px;
  border: 1px solid rgba(220,58,52,0.22); border-radius: var(--radius);
  color: var(--danger); background: var(--danger-soft); font-size: 12px;
}
.retry-full {
  flex-shrink: 0; border: 1px solid currentColor; border-radius: var(--radius-sm);
  padding: 3px 8px; background: transparent; color: inherit; cursor: pointer;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px;
}

.content-text {
  font-family: var(--font-serif);
  font-size: 15px;
  line-height: 2;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
</style>
