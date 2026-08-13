<template>
  <section v-if="aiOutput || isExtracting || extractError" class="extraction-panel" :aria-labelledby="headingId">
    <div class="extraction-panel-header">
      <span :id="headingId" class="ext-title">{{ t('extraction.title') }}</span>
      <span v-if="isExtracting" class="streaming" aria-live="polite">
        <span class="streaming-dot" aria-hidden="true"></span>{{ t('extraction.streaming') }}
      </span>
      <template v-else>
        <span class="result-count">{{ t('extraction.resultCount', { count: entries.length }) }}</span>
        <span class="model-tag">{{ modelName || 'AI' }}</span>
        <button v-if="aiOutput" class="copy-btn" @click.stop="copyOutput" :class="{ copied: justCopied }">
          {{ justCopied ? t('extraction.copied') : t('extraction.copy') }}
        </button>
      </template>
    </div>

    <div v-if="extractError" class="error-banner" role="alert">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="8" cy="8" r="6.2" stroke="currentColor" stroke-width="1.4"/>
        <path d="M8 4.8v3.6M8 11h.01" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span>{{ extractError }}</span>
    </div>

    <div v-if="contextTruncated && !isExtracting" class="context-banner">
      {{ t('extraction.contextTruncated') }}
    </div>

    <!-- 流式阶段保留连续文本，避免半截 token 被错误拆卡。 -->
    <div v-if="isExtracting" class="extraction-body streaming-body">
      <div class="extraction-text md-body" v-html="renderedOutput"></div><span class="cursor"></span>
    </div>

    <!-- 完成后将每条摘录转为独立、可导航的研究卡片。 -->
    <div v-else-if="aiOutput" class="entry-list">
      <component
        v-for="(entry, index) in entries"
        :key="`${index}-${entry.citation}`"
        :is="entry.record ? 'button' : 'article'"
        :type="entry.record ? 'button' : undefined"
        class="entry-card"
        :class="{ matched: Boolean(entry.record), unmatched: !entry.record }"
        v-on="cardListeners(entry.record)"
      >
        <span class="entry-head">
          <span class="entry-number">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="citation-label">{{ entry.citation || t('extraction.unknownCitation') }}</span>
          <span class="match-state" :class="entry.record ? 'verified' : 'unverified'">
            <svg v-if="entry.record" width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.2"/>
              <path d="M4.6 7.1l1.6 1.6 3.3-3.4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ entry.record ? t('extraction.sourceMatched') : t('extraction.sourceUnmatched') }}
          </span>
        </span>

        <span class="entry-content">{{ entry.body }}</span>

        <span v-if="entry.record" class="entry-open">
          <span>{{ t('extraction.viewFullOriginal') }}</span>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M6 3.5L10.5 8L6 12.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <button
          v-else
          type="button"
          class="entry-open"
          disabled
          :title="t('extraction.unmatchedHint')"
        >
          <span>{{ t('extraction.unmatchedHint') }}</span>
        </button>
      </component>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SearchRecord } from '@/stores/search'
import { renderMarkdown } from '@/utils/markdown'
import { parseExtractionEntries } from '@/utils/extraction'
import { useI18n } from '@/i18n'

const props = defineProps<{
  aiOutput: string
  isExtracting: boolean
  extractError?: string
  modelName: string
  sourceRecords: SearchRecord[]
  contextTruncated?: boolean
}>()

const emit = defineEmits<{ 'open-detail': [record: SearchRecord] }>()

const { t } = useI18n()
const justCopied = ref(false)
const headingId = `extraction-heading-${Math.random().toString(36).slice(2, 8)}`
const renderedOutput = computed(() => renderMarkdown(props.aiOutput))

const entries = computed(() => parseExtractionEntries(props.aiOutput, props.sourceRecords))

function cardListeners(record: SearchRecord | null) {
  return record
    ? { click: () => emit('open-detail', record) }
    : {}
}

async function copyOutput() {
  try {
    await navigator.clipboard.writeText(props.aiOutput)
    justCopied.value = true
    setTimeout(() => { justCopied.value = false }, 2000)
  } catch {}
}
</script>

<style scoped>
.extraction-panel { border: 1px solid var(--accent-line); border-radius: var(--radius-lg); overflow: hidden; background: linear-gradient(180deg, rgba(238,243,255,0.52), var(--bg) 120px); box-shadow: 0 8px 24px rgba(47,107,255,0.06); }
.extraction-panel-header { display: flex; align-items: center; gap: 8px; min-height: 42px; padding: 0 14px; border-bottom: 1px solid var(--line); background: rgba(255,255,255,0.76); }
.ext-title { font-size: 13px; font-weight: 650; color: var(--text); }
.result-count { margin-left: 3px; color: var(--text-2); font-size: 11.5px; }
.model-tag { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-2); margin-left: auto; }
.streaming { margin-left: auto; display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--accent); }
.streaming-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: ping 1.4s ease-out infinite; }
@keyframes ping { 0% { box-shadow: 0 0 0 0 rgba(47,107,255,0.35); } 70%, 100% { box-shadow: 0 0 0 5px rgba(47,107,255,0); } }
.copy-btn { height: 25px; padding: 0 9px; font-size: 11.5px; border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--bg); color: var(--text-2); cursor: pointer; }
.copy-btn:hover { border-color: var(--accent); color: var(--accent); }
.copy-btn.copied { border-color: var(--success); color: var(--success); }
.error-banner, .context-banner { padding: 10px 14px; border-bottom: 1px solid var(--line); font-size: 12.5px; }
.error-banner { display: flex; align-items: center; gap: 8px; color: var(--danger); background: var(--danger-soft); }
.context-banner { color: var(--warn); background: #fdf8ee; }

.streaming-body { padding: 18px; }
.extraction-text { display: inline; font-size: 14px; line-height: 1.8; word-break: break-word; color: var(--text); user-select: text; }
.cursor { display: inline-block; width: 2px; height: 15px; vertical-align: -3px; background: var(--accent); margin-left: 2px; animation: blink 1s step-start infinite; }
@keyframes blink { 50% { opacity: 0; } }

.entry-list { display: flex; flex-direction: column; gap: 11px; padding: 14px; }
.entry-card { display: block; width: 100%; overflow: hidden; padding: 0; border: 1px solid var(--line-strong); border-radius: var(--radius-md); background: var(--bg); box-shadow: var(--shadow-sm); color: inherit; font: inherit; text-align: left; appearance: none; transition: border-color var(--transition), box-shadow var(--transition), transform var(--transition); }
.entry-card.matched { cursor: pointer; }
.entry-card.matched:hover { border-color: var(--accent-line); box-shadow: 0 7px 20px rgba(47,107,255,0.09); transform: translateY(-1px); }
.entry-card.matched:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.entry-card.unmatched { border-style: dashed; }
.entry-head { display: flex; align-items: center; gap: 9px; min-height: 36px; padding: 7px 11px; border-bottom: 1px solid var(--line); background: var(--surface); }
.entry-number { align-self: flex-start; flex-shrink: 0; padding-top: 1px; color: var(--accent); font-family: var(--font-mono); font-size: 10.5px; font-weight: 600; }
.citation-label { flex: 1; min-width: 0; color: var(--text-2); font-family: var(--font-mono); font-size: 10.8px; line-height: 1.55; overflow-wrap: anywhere; }
.match-state { display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0; font-size: 10.5px; }
.match-state.verified { color: var(--success); }
.match-state.unverified { color: var(--text-2); }
.entry-content { display: block; padding: 15px 16px 13px; color: var(--text); font-family: var(--font-read); font-size: 14.5px; line-height: 1.85; white-space: pre-wrap; overflow-wrap: anywhere; user-select: text; }
.entry-open { display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 34px; padding: 6px 12px; border: none; border-top: 1px solid var(--line); background: var(--bg); color: var(--accent); font-family: var(--font-ui); font-size: 11.5px; cursor: pointer; text-align: left; }
.entry-open:hover:not(:disabled) { background: var(--accent-soft); }
.entry-open:disabled { color: var(--text-2); background: var(--surface); cursor: not-allowed; }

.md-body :deep(p) { margin: 0 0 10px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(ul), .md-body :deep(ol) { padding-left: 20px; margin: 0 0 10px; }
.md-body :deep(li) { margin-bottom: 5px; }
.md-body :deep(h1), .md-body :deep(h2), .md-body :deep(h3) { font-size: 13px; font-weight: 600; color: var(--text-2); margin: 16px 0 8px; }
.md-body :deep(blockquote) { border-left: 2px solid var(--line-strong); padding-left: 12px; margin: 10px 0; color: var(--text-2); }
.md-body :deep(code) { font-family: var(--font-mono); font-size: 12px; background: var(--surface-3); padding: 1px 5px; border-radius: var(--radius-sm); }
.md-body :deep(pre) { background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 12px; overflow-x: auto; margin: 12px 0; }
.md-body :deep(pre code) { background: none; padding: 0; }
.md-body :deep(strong) { font-weight: 650; }
.md-body :deep(hr) { border: none; border-top: 1px solid var(--line); margin: 14px 0; }

@media (max-width: 720px) {
  .match-state { display: none; }
  .entry-head { align-items: flex-start; }
}
</style>
