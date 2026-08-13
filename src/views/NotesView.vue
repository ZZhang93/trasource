<template>
  <div class="notes-view">
    <!-- ── 左侧笔记列表 ── -->
    <div class="notes-sidebar">
      <div class="notes-sidebar-header">
        <span class="section-title">{{ t('notes.title') }}</span>
        <button class="new-btn" @click="handleNewNote" :title="t('notes.newNote')">+</button>
      </div>

      <!-- 项目筛选 -->
      <div class="project-filter">
        <select v-model="filterProject" class="filter-select">
          <option value="">{{ t('notes.allProjects') }}</option>
          <option
            v-for="p in projectStore.projects"
            :key="p.name"
            :value="p.name"
          >{{ p.name }}</option>
        </select>
      </div>

      <!-- 笔记列表 -->
      <div class="notes-list" v-if="!notesStore.loading">
        <button
          v-for="note in filteredNotes"
          :key="note.id"
          type="button"
          class="note-item"
          :class="{ active: notesStore.currentNote?.id === note.id }"
          :aria-pressed="notesStore.currentNote?.id === note.id"
          @click="selectNote(note)"
        >
          <div class="note-item-title">{{ note.title || t('notes.untitled') }}</div>
          <div class="note-item-meta">
            <span v-if="note.project_name" class="note-project">{{ note.project_name }}</span>
            <span class="note-date">{{ formatDate(note.updated_at) }}</span>
          </div>
          <div v-if="note.tags" class="note-tags">
            <span v-for="tag in splitTags(note.tags)" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>
        </button>

        <div v-if="filteredNotes.length === 0" class="empty-list">
          <p>{{ t('notes.emptyNotes') }}</p>
          <button class="btn-primary" style="font-size:12px;padding:5px 12px" @click="handleNewNote">
            {{ t('notes.newNote') }}
          </button>
        </div>
      </div>
      <div v-else class="loading-text">{{ t('common.loading') }}</div>
    </div>

    <!-- ── 右侧编辑器 ── -->
    <div class="editor-area" v-if="notesStore.currentNote">
      <!-- 标题栏 -->
      <div class="editor-header">
        <input
          v-model="editTitle"
          class="title-input"
          :placeholder="t('notes.titlePlaceholder')"
          @input="markDirty"
        />
        <div class="header-actions">
          <span class="save-status">{{ saveStatus }}</span>
          <button class="tab-btn" :class="{ active: editorMode === 'edit' }" @click="editorMode = 'edit'">{{ t('notes.edit') }}</button>
          <button class="tab-btn" :class="{ active: editorMode === 'preview' }" @click="editorMode = 'preview'">{{ t('notes.preview') }}</button>
          <button class="btn-primary" @click="saveNote" :disabled="!isDirty || isCurrentNoteSaving" style="font-size:12px">
            {{ isCurrentNoteSaving ? t('notes.saving') : t('notes.save') }}
          </button>
          <button class="btn-ghost" @click="exportMd" style="font-size:12px">{{ t('notes.export') }}</button>
          <template v-if="deleteConfirming">
            <button class="del-confirm-yes" @click="doDelete">{{ t('common.delete') }}</button>
            <button class="btn-ghost" style="font-size:12px" @click="deleteConfirming = false">{{ t('common.cancel') }}</button>
          </template>
          <button v-else class="delete-btn" @click="deleteConfirming = true" :title="t('notes.deleteNote')" :aria-label="t('notes.deleteNote')"><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4.5h10M6.2 4.5V3.2a.7.7 0 0 1 .7-.7h2.2a.7.7 0 0 1 .7.7v1.3M4.4 4.5l.5 8.2a.8.8 0 0 0 .8.8h4.6a.8.8 0 0 0 .8-.8l.5-8.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        </div>
      </div>

      <!-- 标签行 -->
      <div class="tags-row">
        <svg class="tags-label" width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2.6 7.3V3.4a.8.8 0 0 1 .8-.8h3.9c.2 0 .4.1.6.2l5 5a.8.8 0 0 1 0 1.2l-3.9 3.9a.8.8 0 0 1-1.2 0l-5-5a.8.8 0 0 1-.2-.6z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><circle cx="5.4" cy="5.4" r="1" fill="currentColor"/></svg>
        <input
          v-model="editTags"
          class="tags-input"
          :placeholder="t('notes.tagsPlaceholder')"
          @input="markDirty"
        />
      </div>

      <!-- 元数据行 -->
      <div class="meta-bar">
        <span v-if="notesStore.currentNote.project_name">{{ notesStore.currentNote.project_name }}</span>
        <span>{{ t('notes.createdAt', { date: formatDate(notesStore.currentNote.created_at) }) }}</span>
        <span>{{ t('notes.updatedAt', { date: formatDate(notesStore.currentNote.updated_at) }) }}</span>
      </div>

      <!-- 编辑 / 预览 -->
      <div class="editor-body">
        <textarea
          v-if="editorMode === 'edit'"
          v-model="editContent"
          class="md-textarea"
          :placeholder="t('notes.editorPlaceholder')"
          @input="markDirty"
          spellcheck="false"
        />
        <div
          v-else
          class="md-preview"
          v-html="renderedContent"
        />
      </div>
    </div>

    <!-- 无笔记选中 -->
    <div v-else class="editor-empty">
      <svg class="empty-icon" width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M6 3.5h7.6L18.5 8.4V20.5H6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M13.4 3.7v4.6h4.6M9 13h6M9 16.5h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <p>{{ t('notes.selectOrCreate') }}</p>
      <button class="btn-primary" @click="handleNewNote">{{ t('notes.newNoteBtn') }}</button>
    </div>

    <!-- 自动保存 toast -->
    <div v-if="showAutoSaveToast" class="autosave-toast">{{ t('notes.autoSaved') }}</div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { renderMarkdown } from '@/utils/markdown'
import { useProjectStore } from '@/stores/project'
import { useNotesStore, type Note } from '@/stores/notes'
import { useUiStore } from '@/stores/ui'
import { useI18n } from '@/i18n'

const { t, locale } = useI18n()
const projectStore = useProjectStore()
const notesStore = useNotesStore()
const ui = useUiStore()

// 筛选
const filterProject = ref(projectStore.currentProjectName || '')

// 编辑状态。revision 在每次用户输入时单调递增，保存响应只有在
// noteId 和 revision 都仍匹配时，才能把当前缓冲区标记为已保存。
const editTitle = ref('')
const editContent = ref('')
const editTags = ref('')
const editorMode = ref<'edit' | 'preview'>('edit')
const isDirty = ref(false)
const showAutoSaveToast = ref(false)
const deleteConfirming = ref(false)
const switchingNote = ref(false)
const creatingNote = ref(false)
let editRevision = 0
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
let autoSaveToastTimer: ReturnType<typeof setTimeout> | null = null
let removeTauriCloseListener: (() => void) | null = null
let componentUnmounted = false
let activeSave: {
  noteId: number
  revision: number
  promise: Promise<boolean>
} | null = null

const isCurrentNoteSaving = computed(() =>
  notesStore.isNoteSaving(notesStore.currentNote?.id),
)

const saveStatus = computed(() => {
  if (isCurrentNoteSaving.value) return t('notes.saving')
  if (!isDirty.value) return t('notes.saved')
  return t('notes.unsaved')
})

// 渲染 Markdown（经 DOMPurify 消毒）
const renderedContent = computed(() => {
  if (!editContent.value) return `<p class="muted">${t('notes.emptyPreview')}</p>`
  return renderMarkdown(editContent.value)
})

// 筛选后的笔记
const filteredNotes = computed(() => {
  if (!filterProject.value) return notesStore.notes
  return notesStore.notes.filter(n => n.project_name === filterProject.value)
})

function clearAutoSaveTimer() {
  if (!autoSaveTimer) return
  clearTimeout(autoSaveTimer)
  autoSaveTimer = null
}

function showSavedToast() {
  showAutoSaveToast.value = true
  if (autoSaveToastTimer) clearTimeout(autoSaveToastTimer)
  autoSaveToastTimer = setTimeout(() => {
    showAutoSaveToast.value = false
    autoSaveToastTimer = null
  }, 2000)
}

function onSaveNote() {
  void saveNote()
}

function handlePageHide() {
  // Browser/Tauri window shutdown cannot await application code, but starting
  // the same queued flush here gives an in-flight keep-alive window. Normal
  // in-app navigation is fully awaited by onBeforeRouteLeave below.
  void flushCurrentNote({ notifyError: false })
}

async function registerTauriCloseFlush() {
  if (!('__TAURI_INTERNALS__' in window)) return
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const appWindow = getCurrentWindow()
    const unlisten = await appWindow.onCloseRequested(async (event) => {
      if (!isDirty.value && !isCurrentNoteSaving.value) return
      event.preventDefault()
      if (await flushCurrentNote()) {
        // destroy() bypasses a second close-request event after the awaited
        // save has completed; the Rust window lifecycle still cleans up the
        // backend sidecar on WindowEvent::Destroyed.
        await appWindow.destroy()
      }
    })
    if (componentUnmounted) unlisten()
    else removeTauriCloseListener = unlisten
  } catch (error) {
    console.warn('Unable to register Tauri close flush:', error)
  }
}

onMounted(async () => {
  window.addEventListener('save-note', onSaveNote)
  window.addEventListener('pagehide', handlePageHide)
  window.addEventListener('beforeunload', handlePageHide)
  void registerTauriCloseFlush()
  try {
    await notesStore.fetchNotes()
  } catch {
    ui.toast(t('notes.loadFailed'), 'error')
  }
})

onBeforeUnmount(() => {
  componentUnmounted = true
  clearAutoSaveTimer()
  if (autoSaveToastTimer) clearTimeout(autoSaveToastTimer)
  removeTauriCloseListener?.()
  removeTauriCloseListener = null
  window.removeEventListener('save-note', onSaveNote)
  window.removeEventListener('pagehide', handlePageHide)
  window.removeEventListener('beforeunload', handlePageHide)
  void flushCurrentNote({ notifyError: false })
})

onBeforeRouteLeave(async () => {
  const saved = await flushCurrentNote()
  return saved || false
})

watch(() => notesStore.currentNote, (note) => {
  clearAutoSaveTimer()
  editRevision += 1
  if (note) {
    editTitle.value = note.title
    editContent.value = note.content_md
    editTags.value = note.tags
  } else {
    editTitle.value = ''
    editContent.value = ''
    editTags.value = ''
  }
  isDirty.value = false
  deleteConfirming.value = false
}, { immediate: true })

async function selectNote(note: Note) {
  if (switchingNote.value || notesStore.currentNote?.id === note.id) return
  switchingNote.value = true
  try {
    if (!await flushCurrentNote()) return
    notesStore.currentNote = note
  } finally {
    switchingNote.value = false
  }
}

function markDirty() {
  editRevision += 1
  isDirty.value = true
}

// 3 秒无输入后自动保存。计时器只决定何时拍快照，真正的写入由 store
// 按 noteId 串行执行，因此手动保存、切换和自动保存不会并发乱序。
watch([editTitle, editContent, editTags], () => {
  if (!isDirty.value) return
  clearAutoSaveTimer()
  autoSaveTimer = setTimeout(() => {
    autoSaveTimer = null
    void persistCurrentNote({ auto: true })
  }, 3000)
})

interface PersistOptions {
  auto?: boolean
  notifyError?: boolean
}

async function persistCurrentNote(options: PersistOptions = {}): Promise<boolean> {
  const note = notesStore.currentNote
  if (!note) return true

  if (!isDirty.value) {
    if (activeSave?.noteId === note.id) return activeSave.promise
    await notesStore.flushNoteSaves(note.id)
    return true
  }

  clearAutoSaveTimer()
  const noteId = note.id
  const revision = editRevision
  const data = {
    title: editTitle.value,
    content_md: editContent.value,
    tags: editTags.value,
  }

  if (activeSave?.noteId === noteId && activeSave.revision === revision) {
    return activeSave.promise
  }

  const promise = (async () => {
    try {
      const result = await notesStore.saveNote(noteId, data, revision)
      const responseIsCurrent =
        notesStore.currentNote?.id === result.noteId
        && editRevision === result.revision

      // New input may have arrived while the request was in flight. In that
      // case it remains dirty and its timer/next flush will persist it.
      if (responseIsCurrent) {
        isDirty.value = false
        if (options.auto) showSavedToast()
      }
      return true
    } catch {
      if (options.notifyError !== false) ui.toast(t('notes.saveFailed'), 'error')
      return false
    }
  })()

  activeSave = { noteId, revision, promise }
  void promise.finally(() => {
    if (activeSave?.promise === promise) activeSave = null
  })
  return promise
}

async function flushCurrentNote(options: PersistOptions = {}): Promise<boolean> {
  const noteId = notesStore.currentNote?.id
  if (noteId == null) return true

  // Input can still arrive while a slow request is being awaited (for example
  // immediately after the user clicks another note). Keep taking and saving
  // fresh snapshots until the same note is actually clean before switching.
  while (notesStore.currentNote?.id === noteId) {
    if (!await persistCurrentNote(options)) return false
    if (!isDirty.value) return true
  }
  return true
}

async function saveNote() {
  await flushCurrentNote()
}

async function handleNewNote() {
  if (creatingNote.value) return
  creatingNote.value = true
  try {
    if (!await flushCurrentNote()) return
    await notesStore.createNote({
      title: t('notes.defaultTitle'),
      content_md: '',
      project_name: filterProject.value || projectStore.currentProjectName || '',
      tags: '',
    })
  } catch {
    ui.toast(t('notes.createFailed'), 'error')
  } finally {
    creatingNote.value = false
  }
}

async function doDelete() {
  const noteId = notesStore.currentNote?.id
  if (noteId == null) return
  deleteConfirming.value = false
  clearAutoSaveTimer()
  try {
    // Drain an already-started write before deleting. Unsaved editor text is
    // intentionally discarded because the user confirmed deletion.
    await notesStore.flushNoteSaves(noteId)
    await notesStore.deleteNote(noteId)
    isDirty.value = false
    ui.toast(t('notes.deleted'), 'success')
  } catch {
    ui.toast(t('notes.deleteFailed'), 'error')
  }
}

function exportMd() {
  if (!notesStore.currentNote) return
  const content = `# ${editTitle.value}\n\n${editContent.value}`
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${editTitle.value || 'note'}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function splitTags(tags: string): string[] {
  return tags.split(',').map(tag => tag.trim()).filter(Boolean)
}

function formatDate(dt: string): string {
  if (!dt) return ''
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return dt
  const diff = Date.now() - d.getTime()
  if (diff >= 0 && diff < 60000) return t('notes.justNow')
  if (diff >= 0 && diff < 3600000) return t('notes.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff >= 0 && diff < 86400000) return t('notes.hoursAgo', { n: Math.floor(diff / 3600000) })
  const dateLocale = locale.value === 'en' ? 'en-US' : 'zh-CN'
  return d.toLocaleDateString(dateLocale, { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.notes-view {
  flex: 1;
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ── 笔记侧边栏 ── */
.notes-sidebar {
  width: 230px;
  min-width: 230px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--sidebar-bg);
}

.notes-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.new-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 4px;
  width: 22px; height: 22px;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  color: var(--text-muted);
  display: flex; align-items: center; justify-content: center;
  transition: all 150ms;
}
.new-btn:hover { color: var(--accent); border-color: var(--accent); }

.project-filter {
  padding: 7px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.filter-select {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 3px 6px;
  font-size: 12px;
  color: var(--text);
  background: var(--bg);
  outline: none;
  cursor: pointer;
}

.notes-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px;
}

.note-item {
  display: block;
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 150ms;
  margin-bottom: 2px;
}
.note-item:hover { background: var(--hover-bg); }
.note-item:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.note-item.active {
  background: var(--hover-bg);
  border-left: 2px solid var(--accent);
  padding-left: 8px;
}

.note-item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 3px;
}

.note-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: var(--text-muted);
}

.note-project {
  background: var(--border);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
  color: var(--text-muted);
}

.note-date { color: var(--text-muted); }

.note-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 4px;
}

.tag-chip {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--accent-soft);
  color: #2383E2;
}

.empty-list {
  text-align: center;
  padding: 40px 16px;
  color: var(--text-muted);
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.loading-text {
  padding: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

/* ── 编辑器 ── */
.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.title-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
  background: transparent;
  font-family: var(--font-ui);
}
.title-input::placeholder { color: var(--text-muted); font-weight: 400; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.save-status {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: 4px;
  min-width: 40px;
  text-align: right;
}

.tab-btn {
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: transparent;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 150ms;
}
.tab-btn.active { background: var(--hover-bg); color: var(--text); border-color: var(--text-muted); }
.tab-btn:hover { border-color: var(--accent); color: var(--accent); }

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 15px;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0.4;
  transition: all 150ms;
}
.delete-btn:hover { opacity: 1; background: #FFF5F5; }

.del-confirm-yes {
  font-size: 12px;
  padding: 3px 10px;
  border: none;
  border-radius: var(--radius);
  background: #e53e3e;
  color: white;
  cursor: pointer;
}
.del-confirm-yes:hover { background: #c53030; }

.tags-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.tags-label { font-size: 13px; }

.tags-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 12px;
  color: var(--text-muted);
  background: transparent;
  font-family: var(--font-ui);
}
.tags-input::placeholder { color: var(--border); }

.meta-bar {
  display: flex;
  gap: 12px;
  padding: 4px 20px;
  font-size: 11px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.editor-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.md-textarea {
  flex: 1;
  resize: none;
  border: none;
  outline: none;
  padding: 20px 28px;
  font-family: 'SF Mono', 'JetBrains Mono', 'Courier New', monospace;
  font-size: 13.5px;
  line-height: 1.85;
  color: var(--text);
  background: var(--bg);
  overflow-y: auto;
}

.md-preview {
  flex: 1;
  overflow-y: auto;
  padding: 20px 32px;
  font-family: var(--font-serif);
  font-size: 15px;
  line-height: 2;
  color: var(--text);
}

/* Markdown 预览样式 */
.md-preview :deep(h1) { font-size: 22px; font-weight: 700; margin: 0 0 20px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.md-preview :deep(h2) { font-size: 17px; font-weight: 600; margin: 24px 0 10px; }
.md-preview :deep(h3) { font-size: 15px; font-weight: 600; margin: 18px 0 8px; }
.md-preview :deep(p) { margin: 0 0 14px; }
.md-preview :deep(blockquote) {
  border-left: 3px solid var(--accent);
  padding: 8px 16px;
  margin: 14px 0;
  color: var(--text-muted);
  background: var(--hover-bg);
  border-radius: 0 var(--radius) var(--radius) 0;
}
.md-preview :deep(ul), .md-preview :deep(ol) { padding-left: 22px; margin: 0 0 14px; }
.md-preview :deep(li) { margin-bottom: 5px; }
.md-preview :deep(code) {
  font-family: 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  background: var(--hover-bg);
  padding: 1px 5px;
  border-radius: 3px;
}
.md-preview :deep(pre) {
  background: var(--sidebar-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  overflow-x: auto;
  margin: 14px 0;
}
.md-preview :deep(pre code) { background: none; padding: 0; }
.md-preview :deep(hr) { border: none; border-top: 1px solid var(--border); margin: 18px 0; }
.md-preview :deep(strong) { font-weight: 700; }
.md-preview :deep(.muted) { color: var(--text-muted); font-style: italic; }

/* 空状态 */
.editor-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);
  background: var(--bg);
}
.empty-icon { color: var(--text-3); opacity: 0.8; }
.editor-empty p { font-size: 14px; }

/* Toast */
.autosave-toast {
  position: fixed;
  bottom: 40px;
  right: 24px;
  background: #333;
  color: #fff;
  font-size: 12px;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  opacity: 0.9;
  z-index: 500;
  pointer-events: none;
}
</style>
