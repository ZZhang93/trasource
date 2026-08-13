<template>
  <aside class="sidebar">
    <!-- 标识 -->
    <div class="sidebar-logo">
      <div class="wordmark">
        <span class="wordmark-zh">问渠</span>
        <span class="wordmark-en data">trasource</span>
      </div>
      <div style="flex:1" />
      <select v-model="currentLocale" class="locale-select" @change="onLocaleChange" :aria-label="t('sidebar.appName')">
        <option value="zh">中</option>
        <option value="en">EN</option>
      </select>
    </div>

    <!-- 搜索导航 -->
    <div class="sidebar-nav">
      <button
        class="sidebar-item"
        :class="{ active: route.name === 'search' }"
        @click="router.push('/search')"
      >
        <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="7.2" cy="7.2" r="4.4" stroke="currentColor" stroke-width="1.4"/>
          <path d="M10.5 10.5L13.5 13.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
        <span>{{ t('sidebar.search') }}</span>
      </button>
    </div>

    <!-- 项目区 -->
    <div class="sidebar-section-title">
      <span>{{ t('sidebar.projects') }}</span>
      <div style="display:flex;gap:4px;align-items:center">
        <button class="icon-btn sort-btn" @click="toggleSort" :title="sortMode === 'recent' ? t('sidebar.sortRecent') : t('sidebar.sortName')">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
            <path d="M2 4h12M4 8h8M6 12h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
        <button class="icon-btn" @click="showNewProject = true" :title="t('sidebar.newProject')">+</button>
      </div>
    </div>

    <div class="project-list">
      <!-- 后端未就绪时明确提示，避免误显示「暂无项目」让用户以为项目丢失 -->
      <div v-if="!backend.ready && !backend.failed" class="empty-hint">
        <span class="starting-dot">◌</span> {{ t('sidebar.backendStarting') }}
      </div>
      <div v-else-if="backend.failed" class="empty-hint">{{ t('sidebar.backendOffline') }}</div>
      <div v-else-if="projectStore.loading" class="muted-text">{{ t('sidebar.loading') }}</div>

      <div
        v-for="project in sortedProjects"
        :key="project.name"
        class="project-item"
        :class="{ active: projectStore.currentProjectName === project.name }"
        @click="selectProject(project.name)"
      >
        <svg class="item-icon-svg" width="14" height="14" viewBox="0 0 16 16" fill="none">
          <path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h3.172a1.5 1.5 0 0 1 1.06.44l.83.83A1.5 1.5 0 0 0 9.62 4.75H12.5A1.5 1.5 0 0 1 14 6.25v6.25A1.5 1.5 0 0 1 12.5 14h-9A1.5 1.5 0 0 1 2 12.5V4.5Z" stroke="currentColor" stroke-width="1.4" fill="none"/>
        </svg>
        <span class="item-name">{{ project.name }}</span>
        <span class="item-badge" v-if="project.record_count && confirmDeleteName !== project.name">
          {{ formatCount(project.record_count) }}
        </span>
        <!-- 删除确认 -->
        <template v-if="confirmDeleteName === project.name">
          <button class="del-confirm-yes" @click.stop="doDeleteProject(project.name)" :title="t('sidebar.confirmDelete')">{{ t('common.delete') }}</button>
          <button class="del-confirm-no" @click.stop="confirmDeleteName = ''" :title="t('common.cancel')">×</button>
        </template>
        <!-- 删除按钮（hover显示） -->
        <button
          v-else
          class="delete-project-btn"
          @click.stop="confirmDeleteName = project.name"
          :title="t('sidebar.deleteProject')"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
            <path d="M3 4h10M6 4V2.5h4V4M5.5 4l.5 9M10.5 4l-.5 9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

      <div v-if="backend.ready && !projectStore.loading && projectStore.projects.length === 0" class="empty-hint">
        {{ t('sidebar.emptyProjects') }}
      </div>
    </div>

    <!-- 当前项目操作 -->
    <div v-if="projectStore.currentProject" class="project-actions">
      <button class="action-btn" @click="showImport = true">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 11V3M8 3L4.8 6.2M8 3l3.2 3.2M2.8 12.5h10.4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ t('sidebar.importLiterature') }}
      </button>
    </div>

    <!-- 最近检索历史 -->
    <div v-if="recentHistory.length > 0" class="sidebar-section-title" style="margin-top:8px">
      <span>{{ t('sidebar.recentSearch') }}</span>
      <button class="icon-btn" @click="clearAllHistory" :title="t('sidebar.clearAll')">×</button>
    </div>
    <div v-if="recentHistory.length > 0" class="history-list">
      <div
        v-for="entry in recentHistory"
        :key="entry.id"
        class="history-item"
        @click="restoreHistory(entry)"
        :title="entry.query"
      >
        <span class="history-query">{{ entry.query }}</span>
        <span class="history-count" v-if="entry.total_found">{{ formatCount(entry.total_found) }}</span>
        <button
          class="history-delete-btn"
          @click.stop="deleteHistoryItem(entry.id)"
          :title="t('sidebar.deleteItem')"
        >×</button>
      </div>
    </div>

    <!-- 弹性空间 -->
    <div style="flex:1" />

    <!-- 底部导航 -->
    <div class="sidebar-bottom">
      <div class="sidebar-divider" />
      <button
        class="sidebar-item"
        :class="{ active: route.name === 'notes' || route.name === 'note-detail' }"
        @click="router.push('/notes')"
      >
        <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M3.5 2.5h6.2l2.8 2.8v8.2H3.5z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
          <path d="M9.6 2.6v3h3M5.8 8.5h4.4M5.8 11h3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <span>{{ t('sidebar.notes') }}</span>
      </button>
      <button class="sidebar-item" @click="showLibrary = true">
        <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="2.6" y="3" width="3.2" height="10" rx="0.8" stroke="currentColor" stroke-width="1.3"/>
          <rect x="6.9" y="3" width="3.2" height="10" rx="0.8" stroke="currentColor" stroke-width="1.3"/>
          <path d="M11.6 4.2l2 9.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <span>{{ t('sidebar.library') }}</span>
      </button>
      <button class="sidebar-item" @click="showSettings = true">
        <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="2.1" stroke="currentColor" stroke-width="1.3"/>
          <path d="M8 1.9v1.6M8 12.5v1.6M14.1 8h-1.6M3.5 8H1.9M12.3 3.7l-1.1 1.1M4.8 11.2l-1.1 1.1M12.3 12.3l-1.1-1.1M4.8 4.8L3.7 3.7" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <span>{{ t('sidebar.settings') }}</span>
      </button>
    </div>

    <!-- ── 新建项目弹窗 ── -->
    <div v-if="showNewProject" class="overlay" @click.self="showNewProject = false">
      <div class="mini-dialog">
        <h3 class="dialog-title">{{ t('sidebar.newProjectTitle') }}</h3>
        <input
          v-model="newProjectName"
          class="input"
          :placeholder="t('sidebar.projectNamePlaceholder')"
          @keydown.enter="createProject"
          @keydown.escape="showNewProject = false"
          autofocus
        />
        <input
          v-model="newProjectDesc"
          class="input"
          :placeholder="t('sidebar.projectDescPlaceholder')"
          style="margin-top: 8px"
        />
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <div class="dialog-footer">
          <button class="btn-ghost" @click="showNewProject = false">{{ t('common.cancel') }}</button>
          <button class="btn-primary" @click="createProject" :disabled="!newProjectName.trim()">
            {{ t('common.create') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 导入弹窗 ── -->
    <ImportDialog
      v-if="showImport && projectStore.currentProject"
      :project-name="projectStore.currentProjectName"
      @close="showImport = false"
      @imported="onImported"
    />

    <!-- ── 文献库弹窗 ── -->
    <LibraryDialog
      v-if="showLibrary"
      @close="showLibrary = false"
      @open-import="showLibrary = false; showImport = true"
    />

    <!-- ── 设置弹窗 ── -->
    <SettingsDialog
      v-if="showSettings"
      @close="showSettings = false"
    />
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { useSearchStore } from '@/stores/search'
import { useBackendStore } from '@/stores/backend'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import ImportDialog from '@/components/dialogs/ImportDialog.vue'
import SettingsDialog from '@/components/dialogs/SettingsDialog.vue'
import LibraryDialog from '@/components/dialogs/LibraryDialog.vue'

const { t, locale, setLocale } = useI18n()
const currentLocale = ref(locale.value)
function onLocaleChange() { setLocale(currentLocale.value) }

const router = useRouter()
const route = useRoute()
const projectStore = useProjectStore()
const searchStore = useSearchStore()
const backend = useBackendStore()

// 历史记录
const recentHistory = ref<any[]>([])
let historyLoadAbort: AbortController | null = null
let historyRestoreAbort: AbortController | null = null
let historyGeneration = 0

const showNewProject = ref(false)
const showImport = ref(false)
const showSettings = ref(false)
const showLibrary = ref(false)

// 项目管理状态
const confirmDeleteName = ref('')  // 当前正在确认删除的项目名

// ── 排序 ──────────────────────────────────────────────────
// 持久化排序模式
const SORT_KEY = 'trasource_sort_mode'
const LAST_OPENED_KEY = 'trasource_last_opened'

const sortMode = ref<'recent' | 'name'>(
  (localStorage.getItem(SORT_KEY) as 'recent' | 'name') || 'recent'
)

// 最近打开时间表 { projectName: timestamp }
const lastOpened = ref<Record<string, number>>(
  JSON.parse(localStorage.getItem(LAST_OPENED_KEY) || '{}')
)

function toggleSort() {
  sortMode.value = sortMode.value === 'recent' ? 'name' : 'recent'
  localStorage.setItem(SORT_KEY, sortMode.value)
}

const sortedProjects = computed(() => {
  const list = [...projectStore.projects]
  if (sortMode.value === 'name') {
    list.sort((a, b) => a.name.localeCompare(b.name, 'zh'))
  } else {
    // 按最近打开时间排序，未记录的排最后
    list.sort((a, b) => {
      const ta = lastOpened.value[a.name] || 0
      const tb = lastOpened.value[b.name] || 0
      return tb - ta
    })
  }
  return list
})

// 全局快捷键事件
function onOpenSettings() { showSettings.value = true }
function onCloseDialogs() {
  showNewProject.value = false
  showImport.value = false
  showSettings.value = false
  showLibrary.value = false
}

async function loadHistory() {
  const projectName = projectStore.currentProjectName
  historyLoadAbort?.abort()
  if (!projectName) {
    recentHistory.value = []
    return
  }
  const controller = new AbortController()
  historyLoadAbort = controller
  const gen = ++historyGeneration
  try {
    const data = await api.get<any[]>(
      `/api/history?project_name=${encodeURIComponent(projectName)}&limit=8`,
      controller.signal,
    )
    if (gen === historyGeneration && projectName === projectStore.currentProjectName) {
      recentHistory.value = data || []
    }
  } catch {}
}

async function deleteHistoryItem(id: number) {
  try {
    await api.delete(`/api/history/${id}`)
    recentHistory.value = recentHistory.value.filter(e => e.id !== id)
  } catch (e) {
    console.error('删除历史记录失败:', e)
  }
}

async function clearAllHistory() {
  if (!projectStore.currentProjectName) return
  try {
    await api.delete(`/api/history?project_name=${encodeURIComponent(projectStore.currentProjectName)}`)
    recentHistory.value = []
  } catch (e) {
    console.error('清空历史记录失败:', e)
  }
}

async function restoreHistory(entry: any) {
  const projectName = projectStore.currentProjectName
  if (!projectName) return
  historyRestoreAbort?.abort()
  const controller = new AbortController()
  historyRestoreAbort = controller
  const gen = ++historyGeneration
  const sessionId = searchStore.beginSession()
  const active = () =>
    !controller.signal.aborted &&
    gen === historyGeneration &&
    sessionId === searchStore.sessionId &&
    projectName === projectStore.currentProjectName

  // 立即使正在进行的搜索/对话失效，避免旧流写入即将恢复的历史会话。
  searchStore.reset()
  searchStore.query = entry.query || ''
  router.push('/search')

  // 1) 列表项不含 ai_output 全文，先按 id 取完整记录
  let full = entry
  try {
    full = await api.get<any>(`/api/history/${entry.id}`, controller.signal)
  } catch {}
  if (!active()) return

  // 2) 重置状态，恢复缓存
  searchStore.query = full.query
  searchStore.language = full.language || 'zh'
  if (full.expansion) searchStore.expansion = full.expansion
  if (full.ai_output) {
    searchStore.aiOutput = full.ai_output
  }
  searchStore.totalFound = full.total_found || 0
  searchStore.hasSearched = true

  // 3) 静默重跑检索恢复 records 和服务端 context（对话依赖 search_id）
  if (full.query) {
    const weightedTokens = full.expansion?.success && full.expansion?.terms
      ? Object.entries(full.expansion.terms).map(([t, w]) => [t, w])
      : null
    searchStore.isSearching = true
    try {
      const result = await api.post<any>('/api/search/execute', {
        query: full.query,
        language: full.language || 'zh',
        project_name: projectName,
        weighted_tokens: weightedTokens,
        top_k: searchStore.topK,
      }, controller.signal)
      if (!active()) return
      searchStore.records = result.records || []
      searchStore.totalFound = result.total_found || searchStore.records.length || 0
      searchStore.searchId = result.search_id || ''
      searchStore.contextChars = result.context_chars || 0
      searchStore.contextRecordIds = (result.context_record_ids || [])
        .map((id: unknown) => Number(id))
        .filter((id: number) => Number.isFinite(id))
      searchStore.contextTruncated = Boolean(result.truncated)
      // 历史摘录只有在重新建立了受项目约束的服务端 context 后，才允许
      // 继续对话；否则会把问题作为无上下文聊天发送。
      searchStore.extractionDone = Boolean(full.ai_output && searchStore.searchId)
    } catch {
      if (active()) searchStore.searchError = t('searchView.searchFailed')
    } finally {
      if (active()) searchStore.isSearching = false
    }
  }
}

onMounted(() => {
  window.addEventListener('open-settings', onOpenSettings)
  window.addEventListener('close-dialogs', onCloseDialogs)
  window.addEventListener('history-updated', loadHistory)
  loadHistory()
})
onUnmounted(() => {
  historyLoadAbort?.abort()
  historyRestoreAbort?.abort()
  historyGeneration += 1
  window.removeEventListener('open-settings', onOpenSettings)
  window.removeEventListener('close-dialogs', onCloseDialogs)
  window.removeEventListener('history-updated', loadHistory)
})

// 当项目切换时刷新历史
watch(() => projectStore.currentProjectName, () => {
  historyRestoreAbort?.abort()
  historyGeneration += 1
  loadHistory()
  confirmDeleteName.value = ''
})

const newProjectName = ref('')
const newProjectDesc = ref('')
const createError = ref('')

function selectProject(name: string) {
  // 记录打开时间
  lastOpened.value[name] = Date.now()
  localStorage.setItem(LAST_OPENED_KEY, JSON.stringify(lastOpened.value))

  projectStore.selectProject(name)
  router.push('/search')
}

async function createProject() {
  const name = newProjectName.value.trim()
  if (!name) return
  createError.value = ''
  try {
    await projectStore.createProject(name, newProjectDesc.value.trim())
    // 新项目记录为"最新"
    lastOpened.value[name] = Date.now()
    localStorage.setItem(LAST_OPENED_KEY, JSON.stringify(lastOpened.value))
    showNewProject.value = false
    newProjectName.value = ''
    newProjectDesc.value = ''
    router.push('/search')
  } catch (e: any) {
    createError.value = e.message || t('sidebar.createFailed')
  }
}

async function doDeleteProject(name: string) {
  try {
    await projectStore.deleteProject(name)
    // 清除该项目的最近打开记录
    delete lastOpened.value[name]
    localStorage.setItem(LAST_OPENED_KEY, JSON.stringify(lastOpened.value))
    confirmDeleteName.value = ''
    // 若还有项目，自动选第一个
    if (projectStore.projects.length > 0) {
      selectProject(sortedProjects.value[0]?.name || projectStore.projects[0].name)
    }
  } catch (e: any) {
    console.error('删除项目失败:', e)
  }
}

async function onImported() {
  await projectStore.fetchProjects()
}

function formatCount(n: number): string {
  if (!n) return ''
  if (n >= 10000) return `${(n / 10000).toFixed(1)}${t('format.wan')}`
  return n.toLocaleString()
}
</script>

<style scoped>
.sidebar {
  width: 232px;
  min-width: 232px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-2);
  border-right: 1px solid var(--line);
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  padding: 0 14px;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}
.wordmark { display: flex; align-items: baseline; gap: 7px; min-width: 0; }
.wordmark-zh {
  font-size: 14px; font-weight: 600; color: var(--text); letter-spacing: 0.01em;
}
.wordmark-en {
  font-size: 10px; color: var(--text-3); letter-spacing: 0.02em;
}

.locale-select {
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  padding: 2px 4px;
  font-size: 10px;
  color: var(--text-2);
  background: var(--bg);
  cursor: pointer;
  outline: none;
  flex-shrink: 0;
}
.locale-select:hover { border-color: var(--text-3); color: var(--text); }

.sidebar-nav { padding: 8px 8px 2px; }

.sidebar-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 26px;
  padding: 0 14px 0 16px;
  margin-top: 10px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-3);
}

.icon-btn {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 16px;
  padding: 0 3px; border-radius: 4px; line-height: 1;
  transition: all 150ms;
}
.icon-btn:hover { color: var(--accent); background: var(--hover-bg); }

.project-list { padding: 0 8px 4px; }

.project-item {
  display: flex; align-items: center; gap: 8px;
  height: 30px; padding: 0 8px; border-radius: var(--radius);
  cursor: pointer; transition: background var(--transition), color var(--transition);
  position: relative; color: var(--text-2);
}
.project-item:hover { background: var(--surface-3); color: var(--text); }
.project-item.active { background: var(--accent-soft); color: var(--accent); }

.item-icon-svg { flex-shrink: 0; opacity: 0.8; }

.item-name {
  font-size: 13px; flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.project-item.active .item-name { font-weight: 500; }
.item-badge {
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-size: 10px; color: var(--text-3);
}
.project-item.active .item-badge { color: var(--accent); opacity: 0.75; }

/* 删除按钮 */
.delete-project-btn {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); padding: 2px 3px; border-radius: 3px;
  opacity: 0; transition: opacity 150ms, color 150ms;
  display: flex; align-items: center; flex-shrink: 0;
}
.project-item:hover .delete-project-btn { opacity: 1; }
.delete-project-btn:hover { color: #e53e3e; }

/* 删除确认按钮 */
.del-confirm-yes {
  font-size: 10px; padding: 1px 6px;
  border: 1px solid #e53e3e; border-radius: 3px;
  background: #fff5f5; color: #e53e3e;
  cursor: pointer; flex-shrink: 0;
}
.del-confirm-yes:hover { background: #e53e3e; color: white; }
.del-confirm-no {
  font-size: 11px; padding: 1px 5px;
  border: 1px solid var(--border); border-radius: 3px;
  background: transparent; color: var(--text-muted);
  cursor: pointer; flex-shrink: 0;
}
.del-confirm-no:hover { background: var(--hover-bg); }

/* 排序按钮 */
.sort-btn { color: var(--text-muted); display: flex; align-items: center; }

.empty-hint { font-size: 12px; color: var(--text-muted); padding: 4px 8px; }
.starting-dot { display: inline-block; animation: spin 2s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.muted-text { font-size: 12px; color: var(--text-muted); padding: 4px 8px; }

.project-actions { padding: 4px 8px 8px; }
.action-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%;
  height: 30px; border-radius: var(--radius);
  border: 1px solid var(--line-strong); background: var(--bg);
  font-size: 12.5px; color: var(--text-2); cursor: pointer;
  transition: border-color var(--transition), color var(--transition);
}
.action-btn:hover { border-color: var(--accent); color: var(--accent); }

.sidebar-bottom { padding: 0 8px 10px; }
.sidebar-divider { height: 1px; background: var(--line); margin: 6px 0 6px; }

/* 历史记录 */
.history-list { padding: 0 8px 4px; }
.history-item {
  display: flex; align-items: center; gap: 8px;
  height: 28px; padding: 0 8px; border-radius: var(--radius);
  cursor: pointer; transition: background var(--transition);
}
.history-item:hover { background: var(--surface-3); }
.history-query {
  font-size: 12.5px; color: var(--text-2);
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.history-item:hover .history-query { color: var(--text); }
.history-count {
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-size: 10px; color: var(--text-3); flex-shrink: 0;
}
.history-delete-btn {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 12px; padding: 0 3px;
  border-radius: 3px; opacity: 0; transition: opacity 150ms, color 150ms;
  flex-shrink: 0; line-height: 1;
}
.history-item:hover .history-delete-btn { opacity: 1; }
.history-delete-btn:hover { color: #e53e3e; }

/* Overlay / dialogs */
.overlay {
  position: fixed; inset: 0;
  background: rgba(23,24,28,0.28);
  backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.mini-dialog {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 20px; width: 320px;
  box-shadow: var(--shadow-lg);
}
.dialog-title { font-size: 14px; font-weight: 600; margin: 0 0 14px; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
.error-text { font-size: 12px; color: #e53e3e; margin: 6px 0 0; }
</style>
