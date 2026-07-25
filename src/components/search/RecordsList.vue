<template>
  <details v-if="totalFound > 0" class="panel" open>
    <summary class="panel-header">
      <span>{{ t('records.totalRecords', { count: totalFound.toLocaleString() }) }}</span>
    </summary>
    <div class="raw-list" ref="listEl">
      <div v-if="!records.length" class="raw-empty">
        <span class="loading-dot">◌</span> {{ t('records.loading') }}
      </div>
      <div
        v-for="(rec, i) in paginatedRecords"
        :key="rec.id"
        class="raw-item"
        @click="$emit('open-detail', rec)"
      >
        <!-- 出处轨：定宽等宽列，纵向对齐可扫读 -->
        <div class="rail">
          <span class="rail-num">{{ (currentPage - 1) * pageSize + i + 1 }}</span>
          <span class="rail-date">{{ rec.date || rec.year || rec.pub_year || '—' }}</span>
        </div>
        <div class="raw-body">
          <p class="raw-content">{{ rec.content?.slice(0, 110) }}{{ rec.content?.length > 110 ? '…' : '' }}</p>
          <div class="raw-foot">
            <span class="source">{{ rec.source_file }}</span>
            <span v-if="rec.page || rec.page_num" class="page">{{ rec.page || rec.page_num }}</span>
          </div>
        </div>
        <span class="row-open" aria-hidden="true">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
            <path d="M6 3.5L10.5 8L6 12.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
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
import { computed, ref, watch } from 'vue'
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

// 翻页后滚回列表顶部
const listEl = ref<HTMLElement | null>(null)
watch(() => props.currentPage, () => {
  listEl.value?.scrollTo({ top: 0 })
})

const paginatedRecords = computed(() => {
  const start = (props.currentPage - 1) * props.pageSize
  return props.records.slice(start, start + props.pageSize)
})

const totalPages = computed(() =>
  Math.ceil(props.records.length / props.pageSize)
)
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

.raw-list { max-height: 42vh; overflow-y: auto; }
.raw-empty {
  padding: 20px; font-size: 12px; color: var(--text-3);
  text-align: center; display: flex; align-items: center; justify-content: center; gap: 7px;
}
.loading-dot {
  width: 11px; height: 11px; border-radius: 50%;
  border: 1.5px solid var(--line-strong); border-top-color: var(--accent);
  animation: spin 0.7s linear infinite; display: inline-block; font-size: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 行：出处轨 + 正文 + 打开指示 */
.raw-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 14px; cursor: pointer;
  border-bottom: 1px solid var(--line);
  transition: background var(--transition);
}
.raw-item:last-of-type { border-bottom: none; }
.raw-item:hover { background: var(--surface); }

.rail {
  display: flex; flex-direction: column; gap: 2px;
  width: 84px; flex-shrink: 0; padding-top: 1px;
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
}
.rail-num { font-size: 10px; color: var(--text-3); }
.rail-date { font-size: 11.5px; color: var(--text-2); letter-spacing: -0.02em; }

.raw-body { flex: 1; min-width: 0; }
.raw-content {
  font-size: 13px; margin: 0 0 4px; color: var(--text); line-height: 1.6;
}
.raw-foot { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-3); }
.source { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px; }
.page { font-family: var(--font-mono); }

.row-open { color: var(--text-3); opacity: 0; flex-shrink: 0; padding-top: 2px; transition: opacity var(--transition); }
.raw-item:hover .row-open { opacity: 1; }

.pagination {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  padding: 8px; border-top: 1px solid var(--line); background: var(--surface);
}
.page-info { font-family: var(--font-mono); font-variant-numeric: tabular-nums; font-size: 11px; color: var(--text-2); }
</style>
