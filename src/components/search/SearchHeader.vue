<template>
  <div class="search-header">
    <div class="search-box-wrap">
      <span class="search-icon">🔍</span>
      <input
        v-model="searchStore.query"
        class="search-input"
        :placeholder="t('search.placeholder')"
        @keydown.enter="$emit('search')"
      />
      <select v-model="searchStore.language" class="lang-select">
        <option value="zh">{{ t('search.langZh') }}</option>
        <option value="en">English</option>
        <option value="mixed">{{ t('search.langMixed') }}</option>
      </select>
      <button
        class="btn-primary"
        @click="$emit('search')"
        :disabled="!searchStore.query.trim() || searchStore.isExpanding || searchStore.isSearching"
      >
        {{ searchStore.isExpanding ? t('search.aiAnalyzing') : searchStore.isSearching ? t('search.searching') : t('search.searchBtn') }}
      </button>
    </div>

    <!-- 高级选项 -->
    <div class="advanced-toggle" @click="showAdvanced = !showAdvanced">
      <span>{{ showAdvanced ? '▴' : '▾' }} {{ t('search.advancedOptions') }}</span>
    </div>
    <div v-if="showAdvanced" class="advanced-panel">
      <div class="adv-row">
        <label>{{ t('search.dateRange') }}</label>
        <input v-model="searchStore.dateFrom" class="adv-input" :placeholder="t('search.dateFromPlaceholder')" maxlength="10" />
        <span class="adv-sep">—</span>
        <input v-model="searchStore.dateTo" class="adv-input" :placeholder="t('search.dateToPlaceholder')" maxlength="10" />
      </div>
      <div class="adv-row">
        <label>{{ t('search.topKLabel') }}</label>
        <input type="range" min="10" max="200" step="10" v-model.number="searchStore.topK" class="adv-slider" />
        <span class="adv-val">{{ t('search.topKUnit', { count: searchStore.topK }) }}</span>
      </div>
      <!-- 文件筛选：多选下拉 -->
      <div class="adv-row adv-row-files">
        <label>{{ t('search.fileFilter') }}</label>
        <div class="file-filter-wrap" @click.stop>
          <div class="file-filter-box" @click="toggleFileDropdown">
            <template v-if="searchStore.fileFilter.length === 0">
              <div class="file-filter-box-row">
                <span class="file-filter-placeholder">{{ t('search.allFiles') }}</span>
                <span class="file-filter-arrow">{{ showFileDropdown ? '▴' : '▾' }}</span>
              </div>
            </template>
            <template v-else>
              <span class="file-chip" v-for="f in searchStore.fileFilter" :key="f">
                <span class="file-chip-name">{{ f }}</span>
                <span class="chip-remove" @click.stop="removeFileFilter(f)">×</span>
              </span>
              <div class="file-filter-box-row" style="margin-top:2px;">
                <span style="font-size:10px;color:var(--text-muted);">{{ t('search.selectedFiles', { count: searchStore.fileFilter.length }) }}</span>
                <span class="file-filter-arrow">{{ showFileDropdown ? '▴' : '▾' }}</span>
              </div>
            </template>
          </div>
          <div v-if="showFileDropdown" class="file-dropdown">
            <div v-if="availableFiles.length === 0" class="file-dropdown-empty">{{ t('search.noFiles') }}</div>
            <label
              v-for="f in availableFiles"
              :key="f"
              class="file-option"
              :class="{ checked: searchStore.fileFilter.includes(f) }"
            >
              <input type="checkbox" :checked="searchStore.fileFilter.includes(f)" @change="toggleFileFilter(f)" />
              <span>{{ f }}</span>
            </label>
            <div class="file-dropdown-actions">
              <button @click="searchStore.fileFilter = []" class="btn-ghost btn-xs">清空</button>
              <button @click="searchStore.fileFilter = [...availableFiles]" class="btn-ghost btn-xs">全选</button>
              <button @click="showFileDropdown = false" class="btn-ghost btn-xs">确定</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useSearchStore } from '@/stores/search'
import { useProjectStore } from '@/stores/project'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'

defineEmits<{ search: [] }>()

const { t } = useI18n()
const searchStore = useSearchStore()
const projectStore = useProjectStore()

const showAdvanced = ref(false)
const showFileDropdown = ref(false)
const availableFiles = ref<string[]>([])

async function loadAvailableFiles() {
  if (!projectStore.currentProjectName) return
  try {
    const data = await api.get<{ files: string[]; total: number }>(
      `/api/library/stats/${encodeURIComponent(projectStore.currentProjectName)}`
    )
    availableFiles.value = data.files || []
  } catch {
    availableFiles.value = []
  }
}

function closeFileDropdownOnOutside() { showFileDropdown.value = false }
function toggleFileDropdown() { showFileDropdown.value = !showFileDropdown.value }
function toggleFileFilter(filename: string) {
  const idx = searchStore.fileFilter.indexOf(filename)
  if (idx >= 0) searchStore.fileFilter.splice(idx, 1)
  else searchStore.fileFilter.push(filename)
}
function removeFileFilter(filename: string) {
  searchStore.fileFilter = searchStore.fileFilter.filter(f => f !== filename)
}

function collapseAdvanced() { showAdvanced.value = false }

onMounted(() => {
  loadAvailableFiles()
  document.addEventListener('click', closeFileDropdownOnOutside)
})
onUnmounted(() => {
  document.removeEventListener('click', closeFileDropdownOnOutside)
})

defineExpose({ loadAvailableFiles, collapseAdvanced })
</script>

<style scoped>
.search-header { padding: 14px 20px 0; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.search-box-wrap { display: flex; align-items: center; gap: 8px; background: var(--bg); border: 1.5px solid var(--border); border-radius: var(--radius-md); padding: 8px 12px; transition: border-color var(--transition); }
.search-box-wrap:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(35,131,226,0.12); }
.search-icon { font-size: 16px; }
.search-input { flex: 1; border: none; outline: none; background: transparent; font-size: 15px; color: var(--text); font-family: var(--font-ui); }
.lang-select { border: none; outline: none; background: transparent; font-size: 12px; color: var(--text-muted); cursor: pointer; }
.advanced-toggle { font-size: 11px; color: var(--text-muted); padding: 6px 2px 8px; cursor: pointer; user-select: none; }
.advanced-toggle:hover { color: var(--accent); }
.advanced-panel { background: var(--sidebar-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; }
.adv-row { display: flex; align-items: center; gap: 8px; }
.adv-row > label { font-size: 11px; color: var(--text-muted); width: 58px; flex-shrink: 0; }
.adv-input { border: 1px solid var(--border); border-radius: var(--radius); padding: 3px 7px; font-size: 12px; color: var(--text); background: var(--bg); outline: none; width: 100px; }
.adv-input:focus { border-color: var(--accent); }
.adv-sep { color: var(--text-muted); font-size: 12px; }
.adv-slider { flex: 1; accent-color: var(--accent); }
.adv-val { font-size: 12px; color: var(--text-muted); min-width: 40px; }
.adv-row-files { align-items: flex-start; }
.file-filter-wrap { flex: 1; position: relative; }
.file-filter-box { display: flex; flex-direction: column; gap: 3px; min-height: 28px; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); cursor: pointer; font-size: 12px; }
.file-filter-box-row { display: flex; align-items: center; justify-content: space-between; }
.file-filter-placeholder { color: var(--text-muted); flex: 1; }
.file-filter-arrow { font-size: 10px; color: var(--text-muted); flex-shrink: 0; margin-left: 4px; }
.file-chip { display: flex; align-items: center; justify-content: space-between; gap: 4px; padding: 3px 8px; background: #EBF4FF; color: var(--accent); border-radius: 3px; font-size: 11px; width: 100%; box-sizing: border-box; overflow: hidden; }
.file-chip-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-remove { cursor: pointer; font-size: 13px; opacity: 0.6; flex-shrink: 0; line-height: 1; }
.chip-remove:hover { opacity: 1; }
.file-dropdown { position: absolute; top: 100%; left: 0; right: 0; z-index: 100; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-lg); max-height: 200px; overflow-y: auto; margin-top: 2px; }
.file-dropdown-empty { padding: 8px 10px; font-size: 12px; color: var(--text-muted); }
.file-option { display: flex; align-items: center; gap: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; transition: background 100ms; }
.file-option:hover { background: var(--hover-bg); }
.file-option.checked { background: #f0f7ff; }
.file-option input[type="checkbox"] { margin: 0; accent-color: var(--accent); }
.file-dropdown-actions { display: flex; gap: 4px; padding: 4px 8px; border-top: 1px solid var(--border); justify-content: flex-end; position: sticky; bottom: 0; background: var(--bg); }
.btn-xs { font-size: 11px; padding: 2px 6px; }
</style>
