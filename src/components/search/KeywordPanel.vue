<template>
  <details
    v-if="expansion && (expansion.intent || Object.keys(expansion.terms || {}).length)"
    class="panel"
    open
  >
    <summary class="panel-header">
      <span class="kw-title">{{ expansion.success === false ? t('keyword.fallbackTitle') : t('keyword.aiAnalysis') }}</span>
      <span v-if="expansion.success === false" class="meta-tag fallback-tag">{{ t('keyword.checkApiKey') }}</span>
      <span v-else-if="expansion.time_range" class="meta-tag">{{ expansion.time_range }}</span>
    </summary>
    <div class="keyword-content">
      <p v-if="expansion.success === false && expansion.error" class="intent fallback-hint">
        {{ t('keyword.fallbackHint', { error: expansion.error }) }}
      </p>
      <p v-else-if="expansion.intent" class="intent">{{ expansion.intent }}</p>
      <div class="terms">
        <span
          v-for="(weight, term) in expansion.terms"
          :key="term"
          class="term-chip"
          :class="getWeightClass(weight as number)"
        >
          {{ term }}<span class="weight">×{{ weight }}</span>
        </span>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { useI18n } from '@/i18n'
const { t } = useI18n()

defineProps<{
  expansion: {
    intent?: string
    time_range?: string | null
    terms?: Record<string, number>
    success?: boolean
    error?: string
  } | null
}>()

function getWeightClass(w: number): string {
  if (w >= 8) return 'weight-high'
  if (w >= 5) return 'weight-mid'
  return 'weight-low'
}
</script>

<style scoped>
.panel { border: 1px solid var(--line); border-radius: var(--radius-md); overflow: hidden; background: var(--bg); }
.panel[open] > .panel-header { border-bottom: 1px solid var(--line); }
.panel-header {
  display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 14px;
  font-size: 12.5px; font-weight: 500; color: var(--text);
  cursor: pointer; user-select: none; list-style: none;
  transition: background var(--transition);
}
.panel-header:hover { background: var(--surface); }
.panel-header::-webkit-details-marker { display: none; }
.panel-header::before {
  content: ''; width: 5px; height: 5px; border-right: 1.4px solid var(--text-3);
  border-bottom: 1.4px solid var(--text-3); transform: rotate(-45deg);
  transition: transform var(--transition); flex-shrink: 0; margin-left: 1px;
}
.panel[open] > .panel-header::before { transform: rotate(45deg); }
.kw-title { flex: 1; }
.meta-tag {
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-size: 11px; color: var(--text-2); background: var(--surface-3);
  padding: 2px 7px; border-radius: var(--radius-sm); margin-left: auto;
}
.fallback-tag { color: var(--warn); background: #FDF6E7; }
.fallback-hint { color: var(--warn); font-size: 12px; }
.keyword-content { padding: 12px 14px 14px; }
.intent { font-size: 13px; line-height: 1.65; color: var(--text-2); margin: 0 0 12px; }
.terms { display: flex; flex-wrap: wrap; gap: 6px; }
/* 权重：以填充强度分三档，数字用等宽 */
.term-chip {
  display: inline-flex; align-items: center; gap: 5px;
  height: 26px; padding: 0 9px; border-radius: var(--radius);
  font-size: 12.5px; line-height: 1;
}
.weight-high { background: var(--accent-soft); color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent-line); }
.weight-mid  { background: var(--surface-2); color: var(--text); box-shadow: inset 0 0 0 1px var(--line); }
.weight-low  { background: transparent; color: var(--text-3); box-shadow: inset 0 0 0 1px var(--line); }
.weight {
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-size: 10px; opacity: 0.65;
}
</style>
