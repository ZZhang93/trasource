<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="library-dialog">

      <!-- 标题栏 -->
      <div class="dialog-header">
        <span class="dialog-title">{{ t('library.title') }}</span>
        <button class="close-btn" @click="$emit('close')">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <path d="M1 1l9 9M10 1L1 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <!-- 主体 -->
      <div class="dialog-body">

        <!-- ─── 左：共享文献库 ─── -->
        <div class="lib-col">
          <div class="col-head">
            <span class="col-label">{{ t('library.sharedLibrary') }}</span>
            <span v-if="sharedStats.total" class="count-chip">{{ t('library.recordCount', { count: formatCount(sharedStats.total) }) }}</span>
          </div>

          <div class="col-list">
            <template v-if="sharedStats.files?.length">
              <div
                v-for="fname in sharedStats.files"
                :key="fname"
                class="file-row"
                :class="{
                  'in-project': isInProject(fname),
                  'confirming': deleteConfirm?.file === fname,
                }"
              >
                <span class="ftype-icon" v-html="fileIcon(fname)"></span>
                <span class="fname">{{ fname }}</span>

                <!-- 正常状态：悬停显示操作按钮 -->
                <template v-if="deleteConfirm?.file !== fname">
                  <!-- 已在项目中 → 显示 ✓ 提示 -->
                  <span v-if="isInProject(fname)" class="in-project-badge">{{ t('library.inProject') }}</span>
                  <!-- 未在项目中 → 显示「加入项目 →」 -->
                  <button
                    v-else
                    class="add-btn"
                    :disabled="addingFile === fname"
                    @click="addToProject(fname)"
                    :title="t('library.addToProjectTooltip')"
                  >
                    {{ addingFile === fname ? t('library.adding') : t('library.addToProject') }}
                    <svg v-if="addingFile !== fname" width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5h6M5.5 2.5L8 5l-2.5 2.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </button>
                  <!-- 删除按钮 -->
                  <button
                    class="trash-btn"
                    @click="startDelete(fname)"
                    :title="t('library.deleteFromLibrary')"
                  >
                    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                      <path d="M2.5 4.5h9M5 4.5V3a.5.5 0 01.5-.5h3a.5.5 0 01.5.5v1.5M4 4.5l.5 7a.5.5 0 00.5.5h4a.5.5 0 00.5-.5l.5-7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                      <path d="M6 7v3M8 7v3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                    </svg>
                  </button>
                </template>

                <!-- 删除二次确认 -->
                <template v-else>
                  <div class="delete-confirm-row">
                    <span v-if="deleteConfirm.projects?.length" class="delete-warning">
                      {{ t('library.usedByProjects', { projects: deleteConfirm.projects.join('、') }) }}
                    </span>
                    <button class="btn-del-confirm" @click="doDelete(fname)">{{ t('library.confirmDelete') }}</button>
                    <button class="btn-del-cancel" @click="deleteConfirm = null">{{ t('common.cancel') }}</button>
                  </div>
                </template>
              </div>
            </template>

            <div v-else class="col-empty">
              <p>{{ t('library.emptyLibrary') }}</p>
              <button class="btn-sm-ghost" @click="$emit('open-import')">{{ t('library.importLiterature') }}</button>
            </div>
          </div>

          <div class="col-foot">
            <button class="btn-ghost" @click="$emit('open-import')">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 1v7M3.5 5L6 7.5 8.5 5M1 10.5h10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              {{ t('library.importLiterature') }}
            </button>
          </div>
        </div>

        <!-- ─── 分隔箭头 ─── -->
        <div class="col-divider">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 8h8M9 5l3 3-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <!-- ─── 右：项目文献（= shared_files 引用）─── -->
        <div class="lib-col">
          <div class="col-head">
            <span class="col-label">{{ t('library.projectFiles') }}</span>
            <div class="proj-tabs" v-if="projectStore.projects.length">
              <button
                v-for="p in projectStore.projects"
                :key="p.name"
                class="proj-tab"
                :class="{ active: selectedProject === p.name }"
                :title="p.name"
                @click="selectProject(p.name)"
              >{{ p.name }}</button>
            </div>
            <span v-if="projectFiles.length" class="count-chip">{{ t('library.fileCount', { count: projectFiles.length }) }}</span>
          </div>

          <div class="col-list">
            <template v-if="projectFiles.length">
              <div
                v-for="fname in projectFiles"
                :key="fname"
                class="file-row"
              >
                <span class="ftype-icon" v-html="fileIcon(fname)"></span>
                <span class="fname">{{ fname }}</span>
                <button
                  class="remove-btn"
                  :disabled="removingFile === fname"
                  @click="removeFromProject(fname)"
                  :title="t('library.removeFromProjectTooltip')"
                >
                  {{ removingFile === fname ? t('library.removing') : t('library.removeFromProject') }}
                </button>
              </div>
            </template>
            <div v-else-if="!selectedProject" class="col-empty">
              <p>{{ t('library.createProjectFirst') }}</p>
            </div>
            <div v-else class="col-empty">
              <p>{{ t('library.noLinkedFiles') }}</p>
              <p class="col-empty-hint">{{ t('library.addFromLibraryHint') }}</p>
            </div>
          </div>

          <div class="col-foot">
            <span v-if="actionMsg" class="feedback" :class="actionMsg.startsWith('✓') ? 'ok' : 'err'">
              {{ actionMsg }}
            </span>
          </div>
        </div>

      </div>

      <!-- 底部 -->
      <div class="dialog-footer">
        <button class="btn-ghost" @click="$emit('close')">{{ t('common.close') }}</button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'

const { t } = useI18n()

const emit = defineEmits<{
  close: []
  'open-import': []
}>()

const projectStore = useProjectStore()

// ── 状态 ──────────────────────────────────────────────────────
const selectedProject = ref(
  projectStore.currentProjectName || projectStore.projects[0]?.name || ''
)
const sharedFiles = ref<string[]>([])
const sharedTotal = ref(0)
const projectFiles = ref<string[]>([])

const addingFile = ref('')
const removingFile = ref('')
const actionMsg = ref('')
const deleteConfirm = ref<{ file: string; projects: string[] } | null>(null)

// ── 计算 ─────────────────────────────────────────────────────
const sharedStats = computed(() => ({ files: sharedFiles.value, total: sharedTotal.value }))

function isInProject(fname: string): boolean {
  return projectFiles.value.includes(fname)
}

// ── 生命周期 ──────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadShared(), loadProjectFiles()])
})

async function loadShared() {
  try {
    const s = await api.get<any>('/api/library/stats/_shared')
    sharedFiles.value = s.files || []
    sharedTotal.value = s.total || 0
  } catch {}
}

async function loadProjectFiles() {
  if (!selectedProject.value) return
  try {
    const s = await api.get<any>(
      `/api/library/stats/${encodeURIComponent(selectedProject.value)}`
    )
    projectFiles.value = s.files || []
  } catch {}
}

async function selectProject(name: string) {
  selectedProject.value = name
  deleteConfirm.value = null
  actionMsg.value = ''
  await loadProjectFiles()
}

// ── 加入项目 ──────────────────────────────────────────────────
async function addToProject(filename: string) {
  if (!selectedProject.value || addingFile.value) return
  addingFile.value = filename
  actionMsg.value = ''
  try {
    await api.post(`/api/projects/${encodeURIComponent(selectedProject.value)}/add-file`, {
      filename,
    })
    projectFiles.value = [...projectFiles.value, filename]
    showMsg(`✓ ${t('library.addedToProject', { project: selectedProject.value })}`)
  } catch {
    showMsg(`✗ ${t('library.addFailed')}`)
  } finally {
    addingFile.value = ''
  }
}

// ── 从项目移除 ────────────────────────────────────────────────
async function removeFromProject(filename: string) {
  if (!selectedProject.value || removingFile.value) return
  removingFile.value = filename
  actionMsg.value = ''
  try {
    await api.delete(
      `/api/projects/${encodeURIComponent(selectedProject.value)}/file/${encodeURIComponent(filename)}`
    )
    projectFiles.value = projectFiles.value.filter(f => f !== filename)
    showMsg(`✓ ${t('library.removedFromProject', { project: selectedProject.value })}`)
  } catch {
    showMsg(`✗ ${t('library.removeFailed')}`)
  } finally {
    removingFile.value = ''
  }
}

// ── 删除共享库文件（二步确认）────────────────────────────────
async function startDelete(filename: string) {
  // 先查询哪些项目在用这个文件
  try {
    const usage = await api.get<any>(
      `/api/library/files/${encodeURIComponent(filename)}/usage`
    )
    deleteConfirm.value = { file: filename, projects: usage.projects || [] }
  } catch {
    deleteConfirm.value = { file: filename, projects: [] }
  }
}

async function doDelete(filename: string) {
  deleteConfirm.value = null
  try {
    await api.delete(`/api/library/files/_shared/${encodeURIComponent(filename)}`)
    sharedFiles.value = sharedFiles.value.filter(f => f !== filename)
    projectFiles.value = projectFiles.value.filter(f => f !== filename)
    showMsg(`✓ ${t('library.deletedFromLibrary', { file: filename })}`)
  } catch {
    showMsg(`✗ ${t('library.deleteFailed')}`)
  }
}

function showMsg(msg: string) {
  actionMsg.value = msg
  setTimeout(() => { actionMsg.value = '' }, 3000)
}

// ── 文件类型图标（灰色 SVG）────────────────────────────────────
function fileIcon(fname: string): string {
  const ext = fname.split('.').pop()?.toLowerCase() || ''

  if (ext === 'csv') return `<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <rect x="1.5" y="1.5" width="11" height="11" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
    <line x1="1.5" y1="5.5" x2="12.5" y2="5.5" stroke="currentColor" stroke-width="1.1"/>
    <line x1="1.5" y1="9"   x2="12.5" y2="9"   stroke="currentColor" stroke-width="1.1"/>
    <line x1="5.5" y1="5.5" x2="5.5"  y2="12.5" stroke="currentColor" stroke-width="1.1"/>
    <line x1="9"   y1="5.5" x2="9"    y2="12.5" stroke="currentColor" stroke-width="1.1"/>
  </svg>`

  if (['epub', 'mobi'].includes(ext)) return `<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <rect x="2" y="1.5" width="8" height="11" rx="1" stroke="currentColor" stroke-width="1.2"/>
    <path d="M10 3h1.5a.5.5 0 01.5.5v9a.5.5 0 01-.5.5H4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="4" y1="4.5" x2="8" y2="4.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="4" y1="6.5" x2="8" y2="6.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="4" y1="8.5" x2="7" y2="8.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
  </svg>`

  const hasLines = ['pdf', 'docx', 'doc', 'txt'].includes(ext)
  return `<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M2.5 1.5h6L11.5 5v7.5a.5.5 0 01-.5.5h-8a.5.5 0 01-.5-.5v-11a.5.5 0 01.5-.5z" stroke="currentColor" stroke-width="1.2"/>
    <path d="M8.5 1.5V5h3" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
    ${hasLines ? `<line x1="4.5" y1="7" x2="9.5" y2="7" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
    <line x1="4.5" y1="9.5" x2="9.5" y2="9.5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>` : ''}
  </svg>`
}

function formatCount(n: number): string {
  if (!n) return ''
  if (n >= 10000) return `${(n / 10000).toFixed(1)}${t('library.tenThousand')}`
  return n.toLocaleString()
}
</script>

<style scoped>
/* ── 遮罩 ── */
.overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 2000;
}
.library-dialog {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 840px;
  max-width: calc(100vw - 40px);
  max-height: 82vh;
  display: flex; flex-direction: column; overflow: hidden;
}

/* ── 标题栏 ── */
.dialog-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 18px 11px;
  border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.dialog-title { font-size: 13.5px; font-weight: 600; color: var(--text); }
.close-btn {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); padding: 3px 5px;
  border-radius: 4px; line-height: 0; transition: all 150ms;
}
.close-btn:hover { background: var(--hover-bg); color: var(--text); }

/* ── 主体 ── */
.dialog-body {
  flex: 1; display: flex; overflow: hidden; min-height: 0;
}

/* ── 列 ── */
.lib-col {
  flex: 1; display: flex; flex-direction: column;
  min-width: 0; overflow: hidden;
}

/* ── 中间分隔箭头 ── */
.col-divider {
  display: flex; align-items: center; justify-content: center;
  width: 32px; flex-shrink: 0;
  color: var(--text-muted);
  border-left: 1px solid var(--border);
  border-right: 1px solid var(--border);
  background: var(--hover-bg);
  opacity: 0.6;
}

/* ── 列头 ── */
.col-head {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px 9px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0; min-height: 42px; overflow: hidden;
}
.col-label {
  font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.07em; text-transform: uppercase;
  color: var(--text-muted); flex-shrink: 0;
}
.count-chip {
  font-size: 10.5px; color: var(--text-muted);
  background: var(--hover-bg); padding: 1px 7px;
  border-radius: 10px; flex-shrink: 0;
}

/* ── 项目标签 ── */
.proj-tabs {
  display: flex; gap: 3px; overflow-x: auto; flex: 1; scrollbar-width: none;
}
.proj-tabs::-webkit-scrollbar { display: none; }
.proj-tab {
  padding: 3px 9px; border-radius: 5px; font-size: 12px;
  border: 1px solid transparent; background: none;
  color: var(--text-muted); cursor: pointer;
  white-space: nowrap; max-width: 130px;
  overflow: hidden; text-overflow: ellipsis;
  transition: all 150ms;
}
.proj-tab:hover { background: var(--hover-bg); color: var(--text); }
.proj-tab.active { background: var(--hover-bg); color: var(--accent); border-color: var(--border); }

/* ── 文件列表 ── */
.col-list { flex: 1; overflow-y: auto; padding: 6px; min-height: 0; }

/* ── 文件行 ── */
.file-row {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 8px; border-radius: 5px;
  transition: background 150ms; min-height: 30px;
  position: relative;
}
.file-row:hover { background: var(--hover-bg); }
.file-row.confirming { background: color-mix(in srgb, #e53e3e 7%, transparent); }
.file-row.in-project { opacity: 0.6; }

.file-row .trash-btn { opacity: 0; }
.file-row:hover .trash-btn { opacity: 1; }
.file-row .add-btn { opacity: 0; }
.file-row:hover .add-btn { opacity: 1; }
.file-row .remove-btn { opacity: 0; }
.file-row:hover .remove-btn { opacity: 1; }

.ftype-icon {
  flex-shrink: 0; color: var(--text-muted);
  display: flex; align-items: center; line-height: 0;
}
.fname {
  flex: 1; font-size: 12.5px; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ── 已在项目中标记 ── */
.in-project-badge {
  flex-shrink: 0; font-size: 10.5px;
  color: var(--accent); opacity: 0;
  white-space: nowrap;
}
.file-row:hover .in-project-badge { opacity: 1; }

/* ── 加入项目按钮 ── */
.add-btn {
  flex-shrink: 0; display: flex; align-items: center; gap: 3px;
  font-size: 11px; padding: 2px 8px;
  border-radius: 4px; border: 1px solid var(--accent);
  background: none; color: var(--accent);
  cursor: pointer; white-space: nowrap;
  transition: all 150ms;
}
.add-btn:hover { background: var(--accent); color: #fff; }
.add-btn:disabled { opacity: 0.5 !important; cursor: not-allowed; }

/* ── 从项目移除按钮 ── */
.remove-btn {
  flex-shrink: 0; font-size: 11px; padding: 2px 8px;
  border-radius: 4px; border: 1px solid var(--border);
  background: none; color: var(--text-muted);
  cursor: pointer; white-space: nowrap; transition: all 150ms;
}
.remove-btn:hover { border-color: #e53e3e; color: #e53e3e; }
.remove-btn:disabled { opacity: 0.5 !important; cursor: not-allowed; }

/* ── 垃圾桶 ── */
.trash-btn {
  flex-shrink: 0; background: none; border: none; cursor: pointer;
  color: var(--text-muted); padding: 3px; border-radius: 4px;
  display: flex; align-items: center;
  transition: color 0.15s, background 0.15s;
}
.trash-btn:hover { color: #e53e3e; background: color-mix(in srgb, #e53e3e 10%, transparent); }

/* ── 删除确认行 ── */
.delete-confirm-row {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
}
.delete-warning {
  font-size: 10.5px; color: #e53e3e; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; max-width: 160px;
}
.btn-del-confirm {
  flex-shrink: 0; font-size: 11px; padding: 2px 8px;
  border-radius: 4px; border: 1px solid #e53e3e;
  background: #e53e3e; color: #fff; cursor: pointer; white-space: nowrap;
}
.btn-del-cancel {
  flex-shrink: 0; font-size: 11px; padding: 2px 8px;
  border-radius: 4px; border: 1px solid var(--border);
  background: var(--bg); color: var(--text-muted); cursor: pointer;
}

/* ── 空状态 ── */
.col-empty {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px;
  padding: 40px 20px; color: var(--text-muted);
  font-size: 12.5px; text-align: center; height: 100%;
}
.col-empty-hint { font-size: 11px; opacity: 0.7; }

/* ── 列底部 ── */
.col-foot {
  padding: 8px 10px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  min-height: 40px;
  display: flex; align-items: center;
}
.feedback { font-size: 11.5px; }
.feedback.ok { color: var(--accent); }
.feedback.err { color: #e53e3e; }

/* ── 对话框底部 ── */
.dialog-footer {
  display: flex; justify-content: flex-end;
  padding: 9px 16px; border-top: 1px solid var(--border); flex-shrink: 0;
}

/* ── 通用按钮 ── */
.btn-ghost {
  display: flex; align-items: center; gap: 5px; font-size: 12.5px;
  padding: 5px 10px; border-radius: var(--radius);
  border: 1px solid var(--border); background: none;
  color: var(--text-muted); cursor: pointer; transition: all 150ms;
}
.btn-ghost:hover { background: var(--hover-bg); color: var(--text); }

.btn-sm-ghost {
  font-size: 11.5px; padding: 4px 10px; border-radius: var(--radius);
  border: 1px solid var(--border); background: none;
  color: var(--text-muted); cursor: pointer; transition: all 150ms;
}
.btn-sm-ghost:hover { background: var(--hover-bg); color: var(--text); }
</style>
