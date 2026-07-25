<template>
  <div v-if="aiOutput || isExtracting || extractError" class="extraction-panel">
    <div class="extraction-panel-header">
      <span class="ext-title">{{ t('extraction.title') }}</span>
      <span v-if="isExtracting" class="streaming">
        <span class="streaming-dot"></span>{{ t('extraction.streaming') }}
      </span>
      <template v-else>
        <span class="model-tag">{{ modelName || 'AI' }}</span>
        <button v-if="aiOutput" class="copy-btn" @click.stop="copyOutput" :class="{ copied: justCopied }">
          {{ justCopied ? t('extraction.copied') : t('extraction.copy') }}
        </button>
      </template>
    </div>

    <!-- 错误横幅（独立于正文展示） -->
    <div v-if="extractError" class="error-banner">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="8" cy="8" r="6.2" stroke="currentColor" stroke-width="1.4"/>
        <path d="M8 4.8v3.6M8 11h.01" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span>{{ extractError }}</span>
    </div>

    <div v-if="aiOutput || isExtracting" class="extraction-body">
      <div class="extraction-text md-body" v-html="renderedOutput"></div><span v-if="isExtracting" class="cursor"></span>
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
.extraction-panel { border: 1px solid var(--line); border-radius: var(--radius-md); overflow: hidden; background: var(--bg); }
.extraction-panel-header {
  display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 14px;
  border-bottom: 1px solid var(--line);
}
.ext-title { font-size: 12.5px; font-weight: 500; color: var(--text); }
.model-tag {
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-3);
  margin-left: auto;
}
.streaming { margin-left: auto; display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--accent); }
.streaming-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
  animation: ping 1.4s ease-out infinite;
}
@keyframes ping {
  0%   { box-shadow: 0 0 0 0 rgba(47,107,255,0.35); }
  70%  { box-shadow: 0 0 0 5px rgba(47,107,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(47,107,255,0); }
}
.copy-btn {
  height: 24px; padding: 0 9px; font-size: 11.5px;
  border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
  background: var(--bg); color: var(--text-2); cursor: pointer;
  transition: border-color var(--transition), color var(--transition);
}
.copy-btn:hover { border-color: var(--accent); color: var(--accent); }
.copy-btn.copied { border-color: var(--success); color: var(--success); }
.error-banner {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; font-size: 12.5px; color: var(--danger);
  background: var(--danger-soft); border-bottom: 1px solid var(--line);
}

/* 阅读面：舒适行距，最大行宽保证可读性 */
.extraction-body { padding: 16px 18px 18px; }
.extraction-text {
  display: inline; font-size: 14px; line-height: 1.8;
  word-break: break-word; color: var(--text); user-select: text;
}
.cursor {
  display: inline-block; width: 2px; height: 15px; vertical-align: -3px;
  background: var(--accent); margin-left: 2px; animation: blink 1s step-start infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* Markdown */
.md-body :deep(p) { margin: 0 0 12px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(ul), .md-body :deep(ol) { padding-left: 20px; margin: 0 0 12px; }
.md-body :deep(li) { margin-bottom: 6px; }
.md-body :deep(h1), .md-body :deep(h2), .md-body :deep(h3) {
  font-size: 13px; font-weight: 600; color: var(--text-2); margin: 18px 0 8px;
}
.md-body :deep(blockquote) { border-left: 2px solid var(--line-strong); padding: 0 0 0 12px; margin: 12px 0; color: var(--text-2); }
.md-body :deep(code) { font-family: var(--font-mono); font-size: 12px; background: var(--surface-3); padding: 1px 5px; border-radius: var(--radius-sm); }
.md-body :deep(pre) { background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 12px; overflow-x: auto; margin: 12px 0; }
.md-body :deep(pre code) { background: none; padding: 0; }
/* 出处（提示词以 **加粗** 标出）→ 等宽小胶囊，与正文明确区分 */
.md-body :deep(strong) {
  display: inline-block;
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-weight: 400; font-size: 11px; line-height: 1.5;
  color: var(--text-2); background: var(--surface-2);
  border: 1px solid var(--line); border-radius: var(--radius-sm);
  padding: 1px 6px; margin: 0 1px; vertical-align: 1px;
  white-space: normal;
}
.md-body :deep(hr) { border: none; border-top: 1px solid var(--line); margin: 14px 0; }

/* 引用来源列表 */
.sources-section { border-top: 1px solid var(--line); background: var(--surface); }
.sources-title {
  padding: 9px 14px 6px; font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3);
}
.sources-list { padding: 0 0 4px; }
.source-item {
  display: flex; align-items: center; gap: 10px; padding: 7px 14px;
  cursor: pointer; transition: background var(--transition);
}
.source-item:hover { background: var(--surface-3); }
.source-num {
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-size: 10px; color: var(--text-3); flex-shrink: 0; width: 16px;
}
.source-info { flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 8px; }
.source-top-row { display: flex; align-items: baseline; gap: 8px; flex-shrink: 0; }
.source-file { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; font-size: 12px; }
.source-date { font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--text-3); font-size: 11px; flex-shrink: 0; }
.source-snippet { color: var(--text-3); font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.source-view-btn { flex-shrink: 0; font-size: 11px; color: var(--accent); padding: 0; opacity: 0; transition: opacity var(--transition); }
.source-item:hover .source-view-btn { opacity: 1; }
</style>
