<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="detail-dialog">
      <!-- 标题栏 -->
      <div class="dialog-header">
        <div class="header-left">
          <span class="doc-type-badge">{{ docTypeLabel }}</span>
          <span class="source-name">{{ record.source_file }}</span>
        </div>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- 元数据行 -->
      <div class="meta-row">
        <span v-if="record.date || record.year" class="meta-tag">
          📅 {{ record.date || record.year }}
        </span>
        <span v-if="record.author" class="meta-tag">✍️ {{ record.author }}</span>
        <span v-if="record.title && record.title !== record.source_file" class="meta-tag">
          📖 {{ record.title }}
        </span>
        <span v-if="record.publisher" class="meta-tag">🏛️ {{ record.publisher }}</span>
        <span v-if="record.pub_year" class="meta-tag">{{ t('detail.year', { year: record.pub_year }) }}</span>
        <span v-if="record.page || record.page_num" class="meta-tag">
          {{ t('detail.page', { page: record.page || record.page_num }) }}
        </span>
        <span v-if="record.chapter" class="meta-tag">{{ record.chapter }}</span>
        <span v-if="record.section" class="meta-tag">{{ record.section }}</span>
        <span v-if="record.interviewee" class="meta-tag">🎙️ {{ record.interviewee }}</span>
        <span v-if="record.interview_date" class="meta-tag">📅 {{ record.interview_date }}</span>
        <span v-if="record.interview_location" class="meta-tag">📍 {{ record.interview_location }}</span>
        <span v-if="record.relevance_score" class="meta-tag score-tag">
          {{ t('detail.relevanceScore', { score: (record.relevance_score * 100).toFixed(0) }) }}
        </span>
      </div>

      <!-- 正文 -->
      <div class="content-area">
        <div class="content-text">{{ record.content }}</div>
      </div>

      <!-- 底部操作 -->
      <div class="dialog-footer">
        <button class="btn-ghost" @click="copyContent">
          {{ copied ? t('detail.copied') : t('detail.copyOriginal') }}
        </button>
        <button class="btn-primary" @click="$emit('create-note', record)">
          {{ t('detail.createNote') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SearchRecord } from '@/stores/search'
import { useI18n } from '@/i18n'

const { t } = useI18n()

const props = defineProps<{ record: SearchRecord }>()
defineEmits<{
  close: []
  'create-note': [record: SearchRecord]
}>()

const copied = ref(false)

const docTypeLabel = computed(() => {
  const map: Record<string, string> = {
    newspaper: `📰 ${t('detail.newspaper')}`,
    book: `📚 ${t('detail.book')}`,
    paper: `📄 ${t('detail.paper')}`,
    interview: `🎙️ ${t('detail.interview')}`,
  }
  return map[props.record.doc_type] || props.record.doc_type || `📄 ${t('detail.literature')}`
})

async function copyContent() {
  try {
    const meta = [
      props.record.source_file,
      props.record.date || props.record.year,
      props.record.author,
      props.record.title !== props.record.source_file ? props.record.title : '',
    ].filter(Boolean).join(' / ')
    await navigator.clipboard.writeText(`${props.record.content}\n\n——${meta}`)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.35);
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
  background: #EBF4FF;
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
