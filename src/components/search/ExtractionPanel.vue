<template>
  <div v-if="aiOutput || isExtracting || extractError" class="extraction-panel">
    <div class="extraction-panel-header">
      <span>{{ t('extraction.title') }}</span>
      <span v-if="isExtracting" class="streaming-dot">●</span>
      <template v-else>
        <span class="model-tag">{{ modelName || 'AI' }}</span>
        <button v-if="aiOutput" class="copy-btn" @click.stop="copyOutput" :class="{ copied: justCopied }">
          {{ justCopied ? t('extraction.copied') : t('extraction.copy') }}
        </button>
      </template>
    </div>

    <!-- 错误横幅（独立于正文展示） -->
    <div v-if="extractError" class="error-banner">
      <span>⚠️ {{ extractError }}</span>
    </div>

    <div v-if="aiOutput || isExtracting" class="extraction-body">
      <div class="extraction-text md-body" v-html="renderedOutput"></div>
      <span v-if="isExtracting" class="cursor">▋</span>
    </div>

    <div v-if="!isExtracting && sourceRecords.length > 0" class="sources-section">
      <div class="sources-title">
        <span>{{ t('extraction.sourcesTitle', { count: sourceRecords.length }) }}</span>
      </div>
      <div class="sources-list">
        <div
          v-for="(rec, i) in sourceRecords"
          :key="rec.id || i"
          class="source-item"
          @click="$emit('open-detail', rec)"
          :title="rec.content?.slice(0, 100)"
        >
          <span class="source-num">{{ i + 1 }}</span>
          <div class="source-info">
            <div class="source-top-row">
              <span class="source-file">{{ rec.source_file }}</span>
              <span class="source-date">{{ rec.date || rec.year || rec.pub_year || '' }}</span>
            </div>
            <div class="source-snippet">{{ rec.content?.slice(0, 80) }}…</div>
          </div>
          <span class="source-view-btn">{{ t('extraction.viewOriginal') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SearchRecord } from '@/stores/search'
import { renderMarkdown } from '@/utils/markdown'
import { useI18n } from '@/i18n'
const { t } = useI18n()

const props = defineProps<{
  aiOutput: string
  isExtracting: boolean
  extractError?: string
  modelName: string
  sourceRecords: SearchRecord[]
}>()

defineEmits<{ 'open-detail': [record: SearchRecord] }>()

const justCopied = ref(false)
const renderedOutput = computed(() => renderMarkdown(props.aiOutput))

async function copyOutput() {
  try {
    await navigator.clipboard.writeText(props.aiOutput)
    justCopied.value = true
    setTimeout(() => { justCopied.value = false }, 2000)
  } catch {}
}
</script>

<style scoped>
.extraction-panel { border: 1px solid var(--border); border-radius: var(--radius-md); }
.extraction-panel-header { display: flex; align-items: center; gap: 8px; padding: 9px 14px; background: var(--sidebar-bg); font-size: 13px; font-weight: 500; border-bottom: 1px solid var(--border); border-radius: var(--radius-md) var(--radius-md) 0 0; }
.model-tag { font-size: 11px; color: var(--text-muted); background: var(--hover-bg); padding: 2px 6px; border-radius: 3px; margin-left: auto; }
.streaming-dot { margin-left: auto; color: var(--accent); animation: blink 1s infinite; font-size: 10px; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
.copy-btn { font-size: 11px; padding: 2px 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); color: var(--text-muted); cursor: pointer; }
.copy-btn:hover { border-color: var(--accent); color: var(--accent); }
.copy-btn.copied { border-color: #38a169; color: #38a169; }
.error-banner { padding: 10px 14px; font-size: 13px; color: #c53030; background: #fff5f5; border-bottom: 1px solid var(--border); }
.extraction-body { padding: 14px 16px; }
.extraction-text { font-family: var(--font-serif); font-size: 14px; line-height: 1.9; word-break: break-word; color: var(--text); user-select: text; }
.cursor { display: inline-block; animation: blink 0.8s infinite; color: var(--accent); }

/* Markdown 元素样式 */
.md-body :deep(p) { margin: 0 0 10px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(ul), .md-body :deep(ol) { padding-left: 22px; margin: 0 0 10px; }
.md-body :deep(li) { margin-bottom: 4px; }
.md-body :deep(h1), .md-body :deep(h2), .md-body :deep(h3) { font-size: 15px; font-weight: 700; margin: 14px 0 8px; }
.md-body :deep(blockquote) { border-left: 3px solid var(--accent); padding: 4px 12px; margin: 10px 0; color: var(--text-muted); }
.md-body :deep(code) { font-family: var(--font-mono); font-size: 12px; background: var(--hover-bg); padding: 1px 5px; border-radius: 3px; }
.md-body :deep(pre) { background: var(--sidebar-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; overflow-x: auto; margin: 10px 0; }
.md-body :deep(pre code) { background: none; padding: 0; }
.md-body :deep(strong) { font-weight: 700; }
.md-body :deep(hr) { border: none; border-top: 1px solid var(--border); margin: 12px 0; }

.sources-section { border-top: 1px solid var(--border); }
.sources-title { padding: 8px 14px 6px; font-size: 12px; font-weight: 600; color: var(--accent); background: var(--sidebar-bg); border-bottom: 1px solid var(--border); }
.sources-list { padding: 0; }
.source-item { display: flex; align-items: center; gap: 8px; padding: 8px 14px; cursor: pointer; font-size: 12px; border-bottom: 1px solid var(--border); transition: background 150ms; }
.source-item:last-child { border-bottom: none; }
.source-item:hover { background: var(--accent-soft); }
.source-num { color: white; background: var(--accent); border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: 700; flex-shrink: 0; }
.source-info { flex: 1; min-width: 0; }
.source-top-row { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.source-file { font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; font-size: 12px; }
.source-date { color: var(--text-muted); font-size: 11px; flex-shrink: 0; }
.source-snippet { color: var(--text-muted); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-view-btn { flex-shrink: 0; font-size: 11px; color: var(--accent); font-weight: 500; padding: 3px 7px; border: 1px solid var(--accent); border-radius: 3px; transition: background 150ms; }
.source-item:hover .source-view-btn { background: var(--accent); color: white; }
</style>
