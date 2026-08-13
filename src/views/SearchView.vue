<template>
  <div class="search-view">
    <!-- 无项目 -->
    <div v-if="!projectStore.currentProjectName" class="empty-state full">
      <svg class="empty-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.3a1.5 1.5 0 0 1 1.06.44l1.2 1.2a1.5 1.5 0 0 0 1.06.44H19.5A1.5 1.5 0 0 1 21 8.58V17.5A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
      </svg>
      <p>{{ t('searchView.noProject') }}</p>
    </div>

    <!-- 正常界面：左列 + 右列 -->
    <template v-else>
      <!-- ── 左主列 ── -->
      <div class="left-column">
        <SearchHeader ref="searchHeaderRef" @search="handleSearch" />

        <!-- 结果滚动区 -->
        <div class="results-scroll">
          <!-- 加载态：三段流程进度（拟词 → 检索 → 摘录） -->
          <div v-if="(searchStore.isExpanding || searchStore.isSearching) && !searchStore.expansion && !searchStore.aiOutput" class="pipeline">
            <div
              v-for="(s, i) in pipelineSteps"
              :key="s.key"
              class="step"
              :class="{ done: i < currentStep, active: i === currentStep }"
            >
              <span class="step-dot"></span>
              <span class="step-label">{{ s.label }}</span>
            </div>
          </div>

          <!-- 搜索错误 -->
          <div v-if="searchStore.searchError && !searchStore.isSearching" class="empty-state">
            <svg class="empty-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" style="color:var(--danger)">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5"/>
              <path d="M12 7.5v5M12 16h.01" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
            <p class="err-text">{{ searchStore.searchError }}</p>
          </div>

          <!-- 无结果（仅在 totalFound 也为 0 时才显示，避免历史恢复时的误判） -->
          <div v-else-if="searchStore.hasSearched && !searchStore.isSearching && !searchStore.records.length && !searchStore.totalFound && !searchStore.searchError" class="empty-state">
            <svg class="empty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M15.5 15.5L20 20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <p>{{ t('searchView.noResults') }}</p>
            <p class="sub">{{ t('searchView.noResultsHint') }}</p>
          </div>

          <!-- 初始空状态：直接给出可点击的起点 -->
          <div v-else-if="!searchStore.hasSearched && !searchStore.isExpanding && !searchStore.isSearching && !searchStore.totalFound" class="start">
            <h2 class="start-title">{{ t('searchView.emptyTitle') }}</h2>
            <p class="start-lead">{{ t('searchView.emptyHint') }}</p>
            <div class="start-examples">
              <span class="start-label">{{ t('searchView.tryLabel') }}</span>
              <button
                v-for="ex in exampleQueries"
                :key="ex"
                class="example-chip"
                @click="runExample(ex)"
              >{{ ex }}</button>
            </div>
          </div>

          <!-- ① AI 关键词分析 -->
          <KeywordPanel :expansion="searchStore.expansion" />

          <!-- 统计栏 -->
          <div v-if="searchStore.totalFound > 0" class="stats-bar">
            <span v-html="t('searchView.statsHits', { count: searchStore.totalFound.toLocaleString() })"></span>
            <span class="stats-sep">·</span>
            <span v-html="t('searchView.statsSentToAI', { count: recordsSentToAi })"></span>
            <template v-if="searchStore.contextChars">
              <span class="stats-sep">·</span>
              <span v-html="t('searchView.statsContext', { count: contextKw })"></span>
            </template>
          </div>

          <!-- ② 原始记录列表 -->
          <RecordsList
            :records="searchStore.records"
            :total-found="searchStore.totalFound"
            :current-page="searchStore.currentPage"
            :page-size="searchStore.pageSize"
            @open-detail="openDetail"
            @page-change="p => searchStore.currentPage = p"
          />

          <!-- ③ AI 史料摘录 -->
          <ExtractionPanel
            :ai-output="searchStore.aiOutput"
            :is-extracting="searchStore.isExtracting"
            :extract-error="searchStore.extractError"
            :model-name="extractionModelName"
            :source-records="sourceRecords"
            :context-truncated="searchStore.contextTruncated"
            @open-detail="openDetail"
          />
        </div>
      </div>

      <!-- ── 右侧对话栏：有可讨论的内容时才占用空间 ── -->
      <ChatPanel
        v-if="searchStore.extractionDone || searchStore.chatMessages.length > 0"
        ref="chatPanelRef"
        :chat-messages="searchStore.chatMessages"
        :is-chat-streaming="searchStore.isChatStreaming"
        :extraction-done="searchStore.extractionDone"
        :ai-output="searchStore.aiOutput"
        :streaming-reply="streamingReply"
        @send-message="sendChat"
      />
    </template>

    <!-- 原文弹窗 -->
    <RecordDetailDialog
      v-if="detailRecord"
      :record="detailRecord"
      @close="detailRecord = null"
      @create-note="onCreateNote"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onUnmounted } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useSearchStore, type SearchRecord } from '@/stores/search'
import { useNotesStore } from '@/stores/notes'
import { useUiStore } from '@/stores/ui'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import RecordDetailDialog from '@/components/dialogs/RecordDetailDialog.vue'
import SearchHeader from '@/components/search/SearchHeader.vue'
import KeywordPanel from '@/components/search/KeywordPanel.vue'
import RecordsList from '@/components/search/RecordsList.vue'
import ExtractionPanel from '@/components/search/ExtractionPanel.vue'
import ChatPanel from '@/components/search/ChatPanel.vue'

const { t, locale } = useI18n()
const projectStore = useProjectStore()
const searchStore = useSearchStore()
const notesStore = useNotesStore()
const ui = useUiStore()

const searchHeaderRef = ref<InstanceType<typeof SearchHeader> | null>(null)
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)
const detailRecord = ref<SearchRecord | null>(null)
const streamingReply = ref('')
const extractionModelName = ref('')

// ── 请求取消与竞态守卫 ──
// 新搜索会 abort 旧的流式请求；generation 防止已 abort 的回调写入新状态
let searchAbort: AbortController | null = null
let chatAbort: AbortController | null = null
let generation = 0
let localSessionId = searchStore.sessionId

onUnmounted(() => {
  searchAbort?.abort()
  chatAbort?.abort()
  // 被取消的请求会因 active() 为 false 而跳过各自 finally；离开页面时
  // 主动收束瞬态状态，回来后不会永久停在“正在处理”。
  searchStore.isExpanding = false
  searchStore.isSearching = false
  searchStore.isExtracting = false
  searchStore.isChatStreaming = false
  streamingReply.value = ''
})

// Sidebar 的历史恢复也会开启新 session；一旦 session 在组件外变化，立即停掉旧流。
watch(() => searchStore.sessionId, (id) => {
  if (id === localSessionId) return
  searchAbort?.abort()
  chatAbort?.abort()
  generation += 1
  streamingReply.value = ''
}, { flush: 'sync' })

// 切换项目时自动清空并中断进行中的请求
watch(() => projectStore.currentProjectName, (n) => {
  if (searchStore.setProject(n || '')) {
    searchAbort?.abort()
    chatAbort?.abort()
    generation += 1
    localSessionId = searchStore.sessionId
    streamingReply.value = ''
    detailRecord.value = null
  }
  if (n) searchHeaderRef.value?.loadAvailableFiles()
}, { immediate: true })

// 三段流程：与后端实际的 拟词 → 检索 → 摘录 对应
const pipelineSteps = computed(() => [
  { key: 'expand',  label: t('searchView.stepExpand') },
  { key: 'search',  label: t('searchView.stepSearch') },
  { key: 'extract', label: t('searchView.stepExtract') },
])
const currentStep = computed(() => {
  if (searchStore.isExpanding) return 0
  if (searchStore.isSearching) return 1
  return 2
})

const exampleQueries = computed<string[]>(() => t('searchView.examples').split('|'))

function runExample(q: string) {
  searchStore.query = q
  handleSearch()
}

const contextKw = computed(() => {
  const n = searchStore.contextChars
  return new Intl.NumberFormat(locale.value === 'en' ? 'en-US' : 'zh-CN', {
    notation: n >= 10_000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(n)
})

const sourceRecords = computed<SearchRecord[]>(() => {
  if (!searchStore.contextRecordIds.length) {
    // 兼容旧后端；新版后端返回实际进入 context 的记录 ID。
    return searchStore.records.slice(0, searchStore.topK)
  }
  const byId = new Map(searchStore.records.map(rec => [String(rec.id), rec]))
  return searchStore.contextRecordIds
    .map(id => byId.get(String(id)))
    .filter((rec): rec is SearchRecord => Boolean(rec))
})

const recordsSentToAi = computed(() =>
  searchStore.contextRecordIds.length || Math.min(searchStore.topK, searchStore.totalFound)
)

function openDetail(rec: SearchRecord) { detailRecord.value = rec }

// 从原文弹窗保存笔记（带引用信息）
async function onCreateNote(rec: SearchRecord) {
  const citation = [
    rec.source_file,
    rec.date || rec.year || rec.pub_year,
    rec.title && rec.title !== rec.source_file ? rec.title : '',
    rec.page || rec.page_num,
  ].filter(Boolean).join(' / ')
  try {
    await notesStore.createNote({
      title: rec.title || rec.source_file,
      content_md: `> ${rec.content.replace(/\n/g, '\n> ')}\n\n—— ${citation}`,
      project_name: projectStore.currentProjectName || '',
      tags: '',
    })
    ui.toast(t('toast.noteCreated'), 'success')
  } catch {
    ui.toast(t('toast.noteCreateFailed'), 'error')
  }
  detailRecord.value = null
}

// ── 流式输出节流：chunk 累积后按帧写入 store，避免每个 token 触发整段重渲染 ──
function createThrottledSink(write: (text: string) => void, intervalMs = 80) {
  let buffer = ''
  let timer: number | null = null
  return {
    push(text: string) {
      buffer += text
      if (timer === null) {
        timer = window.setTimeout(() => {
          timer = null
          if (buffer) { write(buffer); buffer = '' }
        }, intervalMs)
      }
    },
    flush() {
      if (timer !== null) { clearTimeout(timer); timer = null }
      if (buffer) { write(buffer); buffer = '' }
    },
  }
}

// ── 主搜索流程 ──
async function handleSearch() {
  const query = searchStore.query.trim()
  const projectName = projectStore.currentProjectName
  if (!query || !projectName) return

  searchAbort?.abort()
  chatAbort?.abort()
  const sessionId = searchStore.beginSession()
  localSessionId = sessionId
  searchAbort = new AbortController()
  const signal = searchAbort.signal
  const gen = ++generation
  const active = () =>
    gen === generation &&
    sessionId === searchStore.sessionId &&
    projectName === projectStore.currentProjectName &&
    !signal.aborted

  searchStore.reset()
  streamingReply.value = ''
  searchHeaderRef.value?.collapseAdvanced()

  // Step 1: AI 扩展
  searchStore.isExpanding = true
  try {
    const expansion = await api.post<any>('/api/search/expand', {
      query, language: searchStore.language,
      project_name: projectName,
    }, signal)
    if (!active()) return
    searchStore.expansion = expansion
    if (expansion?.success === false) {
      ui.toast(t('toast.expandFallback'), 'info')
    }
  } catch (e: any) {
    if (!active()) return
    console.warn('AI扩展失败:', e)
    searchStore.expansion = { intent: '', time_range: null, terms: {}, success: false }
    ui.toast(t('toast.expandFallback'), 'info')
  } finally {
    if (active()) searchStore.isExpanding = false
  }

  // Step 2: 加权检索
  searchStore.isSearching = true
  try {
    const fileFilterPayload = searchStore.fileFilter.length > 0 ? [...searchStore.fileFilter] : null
    const result = await api.post<any>('/api/search/execute', {
      query, language: searchStore.language,
      project_name: projectName,
      weighted_tokens: searchStore.expansion?.success
        ? Object.entries(searchStore.expansion.terms).map(([t, w]) => [t, w])
        : null,
      date_from: searchStore.dateFrom,
      date_to: searchStore.dateTo,
      file_filter_list: fileFilterPayload,
      top_k: searchStore.topK,
    }, signal)
    if (!active()) return
    searchStore.records = result.records || []
    searchStore.totalFound = result.total_found || 0
    searchStore.searchId = result.search_id || ''
    searchStore.contextChars = result.context_chars || 0
    searchStore.contextRecordIds = (result.context_record_ids || result.contextRecordIds || [])
      .map((id: unknown) => Number(id))
      .filter((id: number) => Number.isFinite(id))
    searchStore.contextTruncated = Boolean(result.truncated)
    searchStore.hasSearched = true
  } catch (e: any) {
    if (!active()) return
    searchStore.searchError = e?.message || t('searchView.searchFailed')
    searchStore.hasSearched = true
    ui.toast(t('toast.searchFailed'), 'error')
  } finally {
    if (active()) searchStore.isSearching = false
  }

  if (!active()) return

  // 立即保存历史记录（检索完成后就保存，不等 AI 提取）
  let historyId: number | null = null
  try {
    const entry = await api.post<any>('/api/history', {
      project_name: projectName,
      query, language: searchStore.language,
      expansion: searchStore.expansion,
      total_found: searchStore.totalFound,
      ai_output: '',
    }, signal)
    if (active()) {
      historyId = entry?.id || null
      window.dispatchEvent(new CustomEvent('history-updated'))
    }
  } catch {}

  // Step 3: AI 流式摘录
  if (searchStore.searchId) {
    searchStore.isExtracting = true
    searchStore.aiOutput = ''
    extractionModelName.value = ''
    const sink = createThrottledSink(text => {
      if (active()) searchStore.aiOutput += text
    })
    try {
      for await (const chunk of api.streamPost('/api/search/extract', {
        query, search_id: searchStore.searchId,
        language: searchStore.language,
        project_name: projectName,
      }, signal)) {
        if (!active()) return
        if (chunk.model !== undefined) {
          extractionModelName.value = chunk.model || ''
          continue
        }
        if (chunk.text) sink.push(chunk.text)
        if (chunk.error) {
          searchStore.extractError = chunk.error
          ui.toast(chunk.error, 'error')
          break
        }
        if (chunk.done) break
      }
    } catch (e: any) {
      if (!active()) return
      if (e?.name !== 'AbortError') {
        searchStore.extractError = t('searchView.extractionFailed')
        ui.toast(t('searchView.extractionFailed'), 'error')
      }
    } finally {
      if (active()) {
        sink.flush()
        searchStore.isExtracting = false
        searchStore.extractionDone = true
        // 提取完成后更新历史记录的 ai_output
        if (historyId && searchStore.aiOutput) {
          try {
            await api.patch(`/api/history/${historyId}`, {
              ai_output: searchStore.aiOutput,
            }, signal)
            if (active()) window.dispatchEvent(new CustomEvent('history-updated'))
          } catch {}
        }
      }
    }
  }
}

// ── AI 对话 ──
async function sendChat(text: string) {
  if (
    !searchStore.extractionDone
    || !searchStore.searchId
    || searchStore.isSearching
    || searchStore.isChatStreaming
  ) return
  const sessionId = searchStore.sessionId
  localSessionId = sessionId
  const projectName = projectStore.currentProjectName
  const searchId = searchStore.searchId
  chatAbort?.abort()
  chatAbort = new AbortController()
  const signal = chatAbort.signal
  const active = () =>
    sessionId === searchStore.sessionId &&
    projectName === projectStore.currentProjectName &&
    searchId === searchStore.searchId &&
    !signal.aborted

  searchStore.chatMessages.push({ role: 'user', content: text })
  const messages = searchStore.chatMessages.map(m => ({ role: m.role, content: m.content }))
  searchStore.isChatStreaming = true
  streamingReply.value = ''
  const sink = createThrottledSink(chunk => {
    if (active()) {
      streamingReply.value += chunk
      chatPanelRef.value?.scrollToBottom()
    }
  })
  let errored = false
  try {
    for await (const chunk of api.streamPost('/api/chat/stream', {
      messages, search_id: searchId,
      language: searchStore.language,
      project_name: projectName,
    }, signal)) {
      if (!active()) return
      if (chunk.text) sink.push(chunk.text)
      if (chunk.error) {
        errored = true
        ui.toast(chunk.error, 'error')
        break
      }
      if (chunk.done) break
    }
    if (!active()) return
    sink.flush()
    if (streamingReply.value) {
      searchStore.chatMessages.push({ role: 'assistant', content: streamingReply.value })
    } else if (errored) {
      searchStore.chatMessages.push({ role: 'assistant', content: t('chat.failed') })
    }
  } catch (error: any) {
    if (active() && error?.name !== 'AbortError') {
      sink.flush()
      searchStore.chatMessages.push({ role: 'assistant', content: t('chat.failed') })
      ui.toast(t('chat.failed'), 'error')
    }
  } finally {
    if (active()) {
      searchStore.isChatStreaming = false
      streamingReply.value = ''
      await nextTick()
      chatPanelRef.value?.scrollToBottom()
    }
  }
}
</script>

<style scoped>
.search-view { flex: 1; display: flex; height: 100%; overflow: hidden; }
.left-column { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.results-scroll { flex: 1; overflow-y: auto; padding: 16px 20px 28px; display: flex; flex-direction: column; gap: 12px; }
/* 各面板按内容自然高度排布，不被 flex 压缩（否则关键词/摘录会被裁切） */
.results-scroll > * { flex-shrink: 0; }

/* 统计条：数字用等宽强调，其余弱化 */
.stats-bar {
  font-size: 12px; color: var(--text-3);
  display: flex; gap: 8px; align-items: baseline; padding: 0 2px 2px;
}
.stats-bar b {
  color: var(--text); font-family: var(--font-mono);
  font-variant-numeric: tabular-nums; font-weight: 500; font-size: 12px;
}
.stats-sep { color: var(--line-strong); }

.empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-2); gap: 8px; padding: 48px 24px; text-align: center; }
.empty-state.full { width: 100%; height: 100%; }
.empty-icon { color: var(--text-3); margin-bottom: 4px; }
.err-text { color: var(--danger); font-size: 13px; }
.sub { font-size: 12px; color: var(--text-3); margin-top: 0; }

/* ── 流程进度：三段，对应真实处理阶段 ── */
.pipeline {
  display: flex; align-items: center; gap: 0;
  align-self: center; margin: 56px 0 0;
  padding: 10px 14px;
  border: 1px solid var(--line); border-radius: var(--radius-md);
  background: var(--surface);
}
.step { display: flex; align-items: center; gap: 7px; padding: 0 12px; position: relative; }
.step + .step::before {
  content: ''; position: absolute; left: -1px; top: 50%;
  width: 14px; height: 1px; background: var(--line-strong); transform: translate(-100%, -50%);
}
.step-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--line-strong); flex-shrink: 0; transition: background var(--transition);
}
.step-label { font-size: 12px; color: var(--text-3); white-space: nowrap; transition: color var(--transition); }
.step.done .step-dot { background: var(--text-3); }
.step.done .step-label { color: var(--text-2); }
.step.active .step-dot { background: var(--accent); animation: ping 1.4s ease-out infinite; }
.step.active .step-label { color: var(--text); font-weight: 500; }
@keyframes ping {
  0%   { box-shadow: 0 0 0 0 rgba(47,107,255,0.35); }
  70%  { box-shadow: 0 0 0 5px rgba(47,107,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(47,107,255,0); }
}

/* ── 起始状态：标题 + 说明 + 可点击示例 ── */
.start {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0;
  padding: 40px 28px; text-align: center;
}
.start-title { font-size: 19px; font-weight: 600; letter-spacing: -0.01em; color: var(--text); margin: 0 0 8px; }
.start-lead { font-size: 13px; line-height: 1.7; color: var(--text-2); margin: 0 0 24px; max-width: 30em; }
.start-examples { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; align-items: center; max-width: 34em; }
.start-label { font-size: 11px; color: var(--text-3); margin-right: 2px; }
.example-chip {
  height: 28px; padding: 0 11px;
  border: 1px solid var(--line-strong); border-radius: 14px;
  background: var(--bg); color: var(--text-2);
  font-size: 12.5px; font-family: var(--font-ui); cursor: pointer;
  transition: border-color var(--transition), color var(--transition), background var(--transition);
}
.example-chip:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
</style>
