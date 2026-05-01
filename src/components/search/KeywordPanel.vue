<template>
  <details
    v-if="expansion && (expansion.intent || Object.keys(expansion.terms || {}).length)"
    class="panel"
    open
  >
    <summary class="panel-header">
      <span>{{ expansion.success === false ? t('keyword.fallbackTitle') : t('keyword.aiAnalysis') }}</span>
      <span v-if="expansion.success === false" class="meta-tag fallback-tag">{{ t('keyword.checkApiKey') }}</span>
      <span v-else-if="expansion.time_range" class="meta-tag">📅 {{ expansion.time_range }}</span>
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
.panel { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: visible; }
.panel[open] > .panel-header { border-bottom: 1px solid var(--border); }
.panel-header { display: flex; align-items: center; gap: 8px; padding: 9px 14px; background: var(--sidebar-bg); font-size: 13px; font-weight: 500; cursor: pointer; user-select: none; list-style: none; }
.panel-header::-webkit-details-marker { display: none; }
.panel-header::before { content: '▸'; font-size: 10px; color: var(--text-muted); transition: transform 150ms; }
.panel[open] > .panel-header::before { transform: rotate(90deg); }
.meta-tag { font-size: 11px; color: var(--text-muted); background: var(--hover-bg); padding: 2px 6px; border-radius: 3px; margin-left: auto; }
.fallback-tag { color: #c05621; background: #fefcbf; }
.fallback-hint { color: #c05621; font-size: 12px; }
.keyword-content { padding: 10px 14px; }
.intent { font-size: 13px; color: var(--text-muted); margin: 0 0 8px; }
.terms { display: flex; flex-wrap: wrap; gap: 6px; }
.term-chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
.weight-high { background: #EBF4FF; color: #2383E2; }
.weight-mid  { background: #F0FFF4; color: #38A169; }
.weight-low  { background: var(--hover-bg); color: var(--text-muted); }
.weight { font-size: 10px; opacity: 0.7; }
</style>
