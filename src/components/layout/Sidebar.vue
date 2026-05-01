<template>
  <aside class="sidebar">
    <!-- App 标题 / Logo -->
    <div class="sidebar-logo">
      <img src="@/assets/logo.png" class="logo-icon-img" :alt="t('sidebar.appName')" />
      <span class="logo-text">{{ t('sidebar.appName') }}</span>
      <div style="flex:1" />
      <select v-model="currentLocale" class="locale-select" @change="onLocaleChange">
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
        <span class="item-icon">🔍</span>
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
      <div v-if="projectStore.loading" class="muted-text">{{ t('sidebar.loading') }}</div>

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

      <div v-if="!projectStore.loading && projectStore.projects.length === 0" class="empty-hint">
        {{ t('sidebar.emptyProjects') }}
      </div>
    </div>

    <!-- 当前项目操作 -->
    <div v-if="projectStore.currentProject" class="project-actions">
      <button class="action-btn" @click="showImport = true">
        <span>⬆️</span> {{ t('sidebar.importLiterature') }}
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
        <span class="history-icon">🕐</span>
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
        <span class="item-icon">📝</span>
        <span>{{ t('sidebar.notes') }}</span>
      </button>
      <button class="sidebar-item" @click="showLibrary = true">
        <span class="item-icon">📚</span>
        <span>{{ t('sidebar.library') }}</span>
      </button>
      <button class="sidebar-item" @click="showSettings = true">
        <span class="item-icon">⚙️</span>
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

// 历史记录
const recentHistory = ref<any[]>([])

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
  if (!projectStore.currentProjectName) return
  try {
    const data = await api.get<any[]>(
      `/api/history?project_name=${encodeURIComponent(projectStore.currentProjectName)}&limit=8`
    )
    recentHistory.value = data || []
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
  // 1) 先重置状态，再恢复缓存
  searchStore.reset()
  searchStore.query = entry.query
  searchStore.language = entry.language || 'zh'
  if (entry.expansion) searchStore.expansion = entry.expansion
  if (entry.ai_output) {
    searchStore.aiOutput = entry.ai_output
    searchStore.extractionDone = true
  }
  searchStore.totalFound = entry.total_found || 0
  searchStore.hasSearched = true

  router.push('/search')

  // 2) 静默加载 records（不显示 loading，不阻塞 UI）
  if (entry.query && projectStore.currentProjectName) {
    const weightedTokens = entry.expansion?.success && entry.expansion?.terms
      ? Object.entries(entry.expansion.terms).map(([t, w]) => [t, w])
      : null
    api.post<any>('/api/search/execute', {
      query: entry.query,
      language: entry.language || 'zh',
      project_name: projectStore.currentProjectName,
      weighted_tokens: weightedTokens,
      top_k: searchStore.topK,
    }).then(result => {
      searchStore.records = result.records || []
      searchStore.totalFound = result.total_found || searchStore.records.length || 0
      searchStore.contextText = result.context || ''
    }).catch(() => {})
  }
}

onMounted(() => {
  window.addEventListener('open-settings', onOpenSettings)
  window.addEventListener('close-dialogs', onCloseDialogs)
  window.addEventListener('history-updated', loadHistory)
  loadHistory()
})
onUnmounted(() => {
  window.removeEventListener('open-settings', onOpenSettings)
  window.removeEventListener('close-dialogs', onCloseDialogs)
  window.removeEventListener('history-updated', loadHistory)
})

// 当项目切换时刷新历史
watch(() => projectStore.currentProjectName, () => {
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
  width: 220px;
  min-width: 220px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.logo-icon-img { width: 24px; height: 24px; object-fit: contain; border-radius: 5px; flex-shrink: 0; }
.logo-text { font-size: 13px; font-weight: 600; color: var(--text); letter-spacing: -0.01em; }

.locale-select {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1px 4px;
  font-size: 10px;
  color: var(--text-muted);
  background: var(--bg);
  cursor: pointer;
  outline: none;
  flex-shrink: 0;
}
.locale-select:hover { border-color: var(--accent); color: var(--text); }

.sidebar-nav { padding: 8px 8px 2px; }

.sidebar-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
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
  display: flex; align-items: center; gap: 6px;
  padding: 5px 8px; border-radius: var(--radius);
  cursor: pointer; transition: background 150ms;
  position: relative;
}
.project-item:hover { background: var(--hover-bg); }
.project-item.active { background: var(--hover-bg); color: var(--accent); }

.item-icon-svg { flex-shrink: 0; color: var(--text-muted); }
.project-item.active .item-icon-svg { color: var(--accent); }

.item-name {
  font-size: 13px; flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.item-badge {
  font-size: 10px; color: var(--text-muted);
  background: var(--border); padding: 1px 5px; border-radius: 10px;
}

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
.muted-text { font-size: 12px; color: var(--text-muted); padding: 4px 8px; }

.project-actions { padding: 2px 8px 8px; }
.action-btn {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 6px 8px; border-radius: var(--radius);
  border: 1px dashed var(--border); background: transparent;
  font-size: 12px; color: var(--text-muted); cursor: pointer;
  transition: all 150ms;
}
.action-btn:hover { border-color: var(--accent); color: var(--accent); background: #f0f7ff; }

.sidebar-bottom { padding: 0 8px 10px; }
.sidebar-divider { height: 1px; background: var(--border); margin: 4px 0 6px; }

.sidebar-item {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 5px 8px; border-radius: var(--radius);
  border: none; background: transparent;
  font-size: 13px; color: var(--text);
  cursor: pointer; text-align: left; transition: background 150ms;
}
.sidebar-item:hover { background: var(--hover-bg); }
.sidebar-item.active { background: var(--hover-bg); color: var(--accent); font-weight: 500; }

/* 历史记录 */
.history-list { padding: 0 8px 4px; }
.history-item {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 8px; border-radius: var(--radius);
  cursor: pointer; transition: background 150ms;
}
.history-item:hover { background: var(--hover-bg); }
.history-icon { font-size: 11px; opacity: 0.6; flex-shrink: 0; }
.history-query {
  font-size: 12px; color: var(--text-muted);
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.history-count {
  font-size: 10px; color: var(--text-muted);
  background: var(--border); padding: 0 4px; border-radius: 3px; flex-shrink: 0;
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
  background: rgba(0,0,0,0.3);
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
