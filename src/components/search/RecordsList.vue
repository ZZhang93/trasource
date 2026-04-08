<template>
  <details v-if="totalFound > 0" class="panel" open>
    <summary class="panel-header">
      <span>{{ t('records.totalRecords', { count: totalFound.toLocaleString() }) }}</span>
    </summary>
    <div class="raw-list">
      <div v-if="!records.length" class="raw-empty">
        <span class="loading-dot">◌</span> {{ t('records.loading') }}
      </div>
      <div
        v-for="(rec, i) in paginatedRecords"
        :key="rec.id"
        class="raw-item"
        @click="$emit('open-detail', rec)"
      >
        <div class="raw-meta">
          <span class="rec-num">{{ (currentPage - 1) * pageSize + i + 1 }}</span>
          <span class="source">{{ rec.source_file }}</span>
          <span class="date">{{ rec.date || rec.year || rec.pub_year }}</span>
          <span class="spacer" />
          <button class="icon-action" :title="t('records.viewOriginal')" @click.stop="$emit('open-detail', rec)">📖</button>
        </div>
        <p class="raw-content">{{ rec.content?.slice(0, 100) }}{{ rec.content?.length > 100 ? '…' : '' }}</p>
      </div>
      <div v-if="totalPages > 1" class="pagination">
        <button class="btn-ghost" @click.stop="$emit('page-change', currentPage - 1)" :disabled="currentPage <= 1">{{ t('records.prevPage') }}</button>
        <span class="page-info">{{ t('records.pageInfo', { current: currentPage, total: totalPages }) }}</span>
        <button class="btn-ghost" @click.stop="$emit('page-change', currentPage + 1)" :disabled="currentPage >= totalPages">{{ t('records.nextPage') }}</button>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchRecord } from '@/stores/search'
import { useI18n } from '@/i18n'
const { t } = useI18n()

const props = defineProps<{
  records: SearchRecord[]
  totalFound: number
  currentPage: number
  pageSize: number
}>()

defineEmits<{
  'open-detail': [record: SearchRecord]
  'page-change': [page: number]
}>()

const paginatedRecords = computed(() => {
  const start = (props.currentPage - 1) * props.pageSize
  return props.records.slice(start, start + props.pageSize)
})

const totalPages = computed(() =>
  Math.ceil(props.records.length / props.pageSize)
)
</script>

<style scoped>
.panel { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: visible; }
.panel[open] > .panel-header { border-bottom: 1px solid var(--border); }
.panel-header { display: flex; align-items: center; gap: 8px; padding: 9px 14px; background: var(--sidebar-bg); font-size: 13px; font-weight: 500; cursor: pointer; user-select: none; list-style: none; }
.panel-header::-webkit-details-marker { display: none; }
.panel-header::before { content: '▸'; font-size: 10px; color: var(--text-muted); transition: transform 150ms; }
.panel[open] > .panel-header::before { transform: rotate(90deg); }
.raw-list { padding: 6px 8px; max-height: 40vh; overflow-y: auto; }
.raw-empty { padding: 12px; font-size: 12px; color: var(--text-muted); text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px; }
.loading-dot { animation: spin 2s linear infinite; display: inline-block; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.raw-item { padding: 6px 10px; border-radius: var(--radius); cursor: pointer; transition: background var(--transition); margin-bottom: 1px; }
.raw-item:hover { background: var(--hover-bg); }
.raw-meta { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); margin-bottom: 2px; }
.rec-num { background: var(--hover-bg); border-radius: 2px; padding: 0 4px; font-size: 10px; flex-shrink: 0; }
.source { font-weight: 500; }
.date { color: var(--text-muted); }
.spacer { flex: 1; }
.icon-action { background: none; border: none; cursor: pointer; font-size: 12px; padding: 1px 3px; border-radius: 3px; opacity: 0; transition: opacity 150ms; }
.raw-item:hover .icon-action { opacity: 1; }
.raw-content { font-size: 13px; margin: 0; color: var(--text); line-height: 1.5; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 8px; border-top: 1px solid var(--border); }
.page-info { font-size: 12px; color: var(--text-muted); }
</style>
