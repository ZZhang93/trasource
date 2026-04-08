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
        <div
          v-for="note in filteredNotes"
          :key="note.id"
          class="note-item"
          :class="{ active: notesStore.currentNote?.id === note.id }"
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
        </div>

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
          <button class="btn-primary" @click="saveNote" :disabled="!isDirty || notesStore.saving" style="font-size:12px">
            {{ notesStore.saving ? t('notes.saving') : t('notes.save') }}
          </button>
          <button class="btn-ghost" @click="exportMd" style="font-size:12px">{{ t('notes.export') }}</button>
          <button class="delete-btn" @click="confirmDelete" :title="t('notes.deleteNote')">🗑️</button>
        </div>
      </div>

      <!-- 标签行 -->
      <div class="tags-row">
        <span class="tags-label">🏷️</span>
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
      <div class="empty-icon">📝</div>
      <p>{{ t('notes.selectOrCreate') }}</p>
      <button class="btn-primary" @click="handleNewNote">{{ t('notes.newNoteBtn') }}</button>
    </div>

    <!-- 自动保存 toast -->
    <div v-if="showAutoSaveToast" class="autosave-toast">{{ t('notes.autoSaved') }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { useProjectStore } from '@/stores/project'
import { useNotesStore, type Note } from '@/stores/notes'
import { useI18n } from '@/i18n'

const { t } = useI18n()
const projectStore = useProjectStore()
const notesStore = useNotesStore()

// 筛选
const filterProject = ref(projectStore.currentProjectName || '')

// 编辑状态
const editTitle = ref('')
const editContent = ref('')
const editTags = ref('')
const editorMode = ref<'edit' | 'preview'>('edit')
const isDirty = ref(false)
const showAutoSaveToast = ref(false)

const saveStatus = computed(() => {
  if (notesStore.saving) return t('notes.saving')
  if (!isDirty.value) return t('notes.saved')
  return t('notes.unsaved')
})

// 渲染 Markdown
const renderedContent = computed(() => {
  if (!editContent.value) return `<p class="muted">${t('notes.emptyPreview')}</p>`
  return marked.parse(editContent.value) as string
})

// 筛选后的笔记
const filteredNotes = computed(() => {
  if (!filterProject.value) return notesStore.notes
  return notesStore.notes.filter(n => n.project_name === filterProject.value)
})

function onSaveNote() { saveNote() }

onMounted(async () => {
  await notesStore.fetchNotes()
  window.addEventListener('save-note', onSaveNote)
})

onUnmounted(() => {
  window.removeEventListener('save-note', onSaveNote)
})

watch(() => notesStore.currentNote, (note) => {
  if (note) {
    editTitle.value = note.title
    editContent.value = note.content_md
    editTags.value = note.tags
    isDirty.value = false
  }
})

function selectNote(note: Note) {
  if (isDirty.value) autoSave()
  notesStore.currentNote = note
}

function markDirty() {
  isDirty.value = true
}

// 3秒自动保存
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
watch([editTitle, editContent, editTags], () => {
  if (!isDirty.value) return
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => autoSave(), 3000)
})

async function autoSave() {
  if (!notesStore.currentNote || !isDirty.value) return
  await notesStore.saveNote(notesStore.currentNote.id, {
    title: editTitle.value,
    content_md: editContent.value,
    tags: editTags.value,
  })
  isDirty.value = false
  showAutoSaveToast.value = true
  setTimeout(() => { showAutoSaveToast.value = false }, 2000)
}

async function saveNote() {
  if (!notesStore.currentNote) return
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  await notesStore.saveNote(notesStore.currentNote.id, {
    title: editTitle.value,
    content_md: editContent.value,
    tags: editTags.value,
  })
  isDirty.value = false
}

async function handleNewNote() {
  const note = await notesStore.createNote({
    title: t('notes.defaultTitle'),
    content_md: '',
    project_name: filterProject.value || projectStore.currentProjectName || '',
    tags: '',
  })
  notesStore.currentNote = note
}

async function confirmDelete() {
  if (!notesStore.currentNote) return
  if (!confirm(t('notes.confirmDelete', { title: notesStore.currentNote.title }))) return
  await notesStore.deleteNote(notesStore.currentNote.id)
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
  return tags.split(',').map(t => t.trim()).filter(Boolean)
}

function formatDate(dt: string): string {
  if (!dt) return ''
  const d = new Date(dt.replace('T', ' '))
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return t('notes.justNow')
  if (diff < 3600000) return t('notes.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('notes.hoursAgo', { n: Math.floor(diff / 3600000) })
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
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
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 150ms;
  margin-bottom: 2px;
}
.note-item:hover { background: var(--hover-bg); }
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
  background: #EBF4FF;
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
.empty-icon { font-size: 48px; opacity: 0.35; }
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
