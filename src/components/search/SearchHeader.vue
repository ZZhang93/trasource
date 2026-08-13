<template>
  <div class="search-header">
    <div class="search-box-wrap">
      <svg class="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="7.2" cy="7.2" r="4.6" stroke="currentColor" stroke-width="1.4"/>
        <path d="M10.6 10.6L13.6 13.6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
      <input
        v-model="searchStore.query"
        class="search-input"
        :placeholder="t('search.placeholder')"
        @keydown.enter="$emit('search')"
      />
      <button
        v-if="searchStore.query"
        class="clear-btn"
        :title="t('common.clear')"
        :aria-label="t('common.clear')"
        @click="searchStore.query = ''"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
      </button>
      <select v-model="searchStore.language" class="lang-select" :aria-label="t('search.langZh')">
        <option value="zh">{{ t('search.langZh') }}</option>
        <option value="en">English</option>
        <option value="mixed">{{ t('search.langMixed') }}</option>
      </select>
      <button
        class="btn-primary search-btn"
        @click="$emit('search')"
        :disabled="!searchStore.query.trim() || searchStore.isExpanding || searchStore.isSearching"
      >
        {{ searchStore.isExpanding || searchStore.isSearching ? t('search.searching') : t('search.searchBtn') }}
      </button>
    </div>

    <!-- 高级选项 -->
    <button
      type="button"
      class="advanced-toggle"
      :aria-expanded="showAdvanced"
      @click="showAdvanced = !showAdvanced"
    >
      <span>{{ showAdvanced ? '▴' : '▾' }} {{ t('search.advancedOptions') }}</span>
    </button>
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
          <div class="file-filter-box">
            <template v-if="searchStore.fileFilter.length === 0">
              <button
                type="button"
                class="file-filter-toggle file-filter-box-row"
                aria-haspopup="listbox"
                :aria-expanded="showFileDropdown"
                @click="toggleFileDropdown"
              >
                <span class="file-filter-placeholder">{{ t('search.allFiles') }}</span>
                <span class="file-filter-arrow">{{ showFileDropdown ? '▴' : '▾' }}</span>
              </button>
            </template>
            <template v-else>
              <span class="file-chip" v-for="f in searchStore.fileFilter" :key="f">
                <span class="file-chip-name">{{ f }}</span>
                <button
                  type="button"
                  class="chip-remove"
                  :aria-label="`${t('common.clear')} ${f}`"
                  @click.stop="removeFileFilter(f)"
                >×</button>
              </span>
              <button
                type="button"
                class="file-filter-toggle file-filter-box-row"
                style="margin-top:2px;"
                aria-haspopup="listbox"
                :aria-expanded="showFileDropdown"
                @click="toggleFileDropdown"
              >
                <span style="font-size:10px;color:var(--text-muted);">{{ t('search.selectedFiles', { count: searchStore.fileFilter.length }) }}</span>
                <span class="file-filter-arrow">{{ showFileDropdown ? '▴' : '▾' }}</span>
              </button>
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
              <button @click="searchStore.fileFilter = []" class="btn-ghost btn-xs">{{ t('common.clear') }}</button>
              <button @click="searchStore.fileFilter = [...availableFiles]" class="btn-ghost btn-xs">{{ t('common.selectAll') }}</button>
              <button @click="showFileDropdown = false" class="btn-ghost btn-xs">{{ t('common.ok') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
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
let filesAbort: AbortController | null = null
let filesGeneration = 0

watch(() => searchStore.topK, value => {
  localStorage.setItem('trasource_search_top_k', String(value))
})

async function loadAvailableFiles() {
  const projectName = projectStore.currentProjectName
  filesAbort?.abort()
  filesAbort = null
  const generation = ++filesGeneration
  availableFiles.value = []
  showFileDropdown.value = false
  if (!projectName) return

  const controller = new AbortController()
  filesAbort = controller
  const active = () =>
    generation === filesGeneration &&
    projectName === projectStore.currentProjectName &&
    !controller.signal.aborted

  try {
    const data = await api.get<{ files: string[]; total: number }>(
      `/api/library/stats/${encodeURIComponent(projectName)}`,
      controller.signal,
    )
    if (active()) availableFiles.value = data.files || []
  } catch {
    if (active()) availableFiles.value = []
  } finally {
    if (filesAbort === controller) filesAbort = null
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
  filesAbort?.abort()
  filesGeneration += 1
  document.removeEventListener('click', closeFileDropdownOnOutside)
})

defineExpose({ loadAvailableFiles, collapseAdvanced })
</script>

<style scoped>
.search-header { padding: 14px 20px 0; border-bottom: 1px solid var(--line); flex-shrink: 0; background: var(--bg); }
.search-box-wrap {
  display: flex; align-items: center; gap: 8px;
  background: var(--bg); border: 1px solid var(--line-strong);
  border-radius: var(--radius-md); padding: 5px 5px 5px 12px;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.search-box-wrap:focus-within { border-color: var(--accent); box-shadow: var(--ring); }
.search-icon { color: var(--text-3); flex-shrink: 0; }
.search-box-wrap:focus-within .search-icon { color: var(--accent); }
.search-input {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 14px; color: var(--text); font-family: var(--font-ui);
  height: 32px;
}
.search-input::placeholder { color: var(--text-3); }
.clear-btn {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; flex-shrink: 0;
  border: none; background: transparent; border-radius: 50%;
  color: var(--text-3); cursor: pointer; transition: background var(--transition), color var(--transition);
}
.clear-btn:hover { background: var(--surface-3); color: var(--text); }
.lang-select {
  border: none; outline: none; background: transparent;
  font-size: 12px; color: var(--text-2); cursor: pointer;
  font-family: var(--font-ui); flex-shrink: 0;
}
.search-btn { min-width: 64px; }
.advanced-toggle {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--text-3); padding: 8px 2px 10px;
  border: 0; background: transparent; font-family: inherit;
  cursor: pointer; user-select: none;
}
.advanced-toggle:hover { color: var(--text); }
.advanced-toggle:focus-visible, .file-filter-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
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
.file-filter-box { display: flex; flex-direction: column; gap: 3px; min-height: 28px; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); font-size: 12px; }
.file-filter-box-row { display: flex; align-items: center; justify-content: space-between; }
.file-filter-toggle { width: 100%; padding: 0; border: 0; background: transparent; color: inherit; font: inherit; cursor: pointer; text-align: left; }
.file-filter-placeholder { color: var(--text-muted); flex: 1; }
.file-filter-arrow { font-size: 10px; color: var(--text-muted); flex-shrink: 0; margin-left: 4px; }
.file-chip { display: flex; align-items: center; justify-content: space-between; gap: 4px; padding: 3px 8px; background: var(--accent-soft); color: var(--accent); border-radius: 3px; font-size: 11px; width: 100%; box-sizing: border-box; overflow: hidden; }
.file-chip-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-remove { padding: 0; border: 0; background: transparent; color: inherit; cursor: pointer; font-size: 13px; opacity: 0.6; flex-shrink: 0; line-height: 1; }
.chip-remove:hover { opacity: 1; }
.file-dropdown { position: absolute; top: 100%; left: 0; right: 0; z-index: 100; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-lg); max-height: 200px; overflow-y: auto; margin-top: 2px; }
.file-dropdown-empty { padding: 8px 10px; font-size: 12px; color: var(--text-muted); }
.file-option { display: flex; align-items: center; gap: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; transition: background 100ms; }
.file-option:hover { background: var(--hover-bg); }
.file-option.checked { background: var(--accent-soft); }
.file-option input[type="checkbox"] { margin: 0; accent-color: var(--accent); }
.file-dropdown-actions { display: flex; gap: 4px; padding: 4px 8px; border-top: 1px solid var(--border); justify-content: flex-end; position: sticky; bottom: 0; background: var(--bg); }
.btn-xs { font-size: 11px; padding: 2px 6px; }
</style>
