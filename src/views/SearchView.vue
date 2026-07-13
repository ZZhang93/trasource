<template>
  <div class="search-view">
    <!-- 无项目 -->
    <div v-if="!projectStore.currentProjectName" class="empty-state full">
      <div class="empty-icon">📁</div>
      <p>{{ t('searchView.noProject') }}</p>
    </div>

    <!-- 正常界面：左列 + 右列 -->
    <template v-else>
      <!-- ── 左主列 ── -->
      <div class="left-column">
        <SearchHeader ref="searchHeaderRef" @search="handleSearch" />

        <!-- 结果滚动区 -->
        <div class="results-scroll">
          <!-- 加载态（仅新搜索时显示，历史恢复时不显示全屏 loading） -->
          <div v-if="(searchStore.isExpanding || searchStore.isSearching) && !searchStore.expansion && !searchStore.aiOutput" class="loading-state">
            <div class="spinner">◌</div>
            <p>{{ searchStore.isExpanding ? t('searchView.aiAnalyzing') : t('searchView.searching') }}</p>
          </div>

          <!-- 搜索错误 -->
          <div v-if="searchStore.searchError && !searchStore.isSearching" class="empty-state">
            <div class="empty-icon sm">⚠️</div>
            <p class="err-text">{{ searchStore.searchError }}</p>
          </div>

          <!-- 无结果（仅在 totalFound 也为 0 时才显示，避免历史恢复时的误判） -->
          <div v-else-if="searchStore.hasSearched && !searchStore.isSearching && !searchStore.records.length && !searchStore.totalFound && !searchStore.searchError" class="empty-state">
            <div class="empty-icon sm">🔍</div>
            <p>{{ t('searchView.noResults') }}</p>
            <p class="sub">{{ t('searchView.noResultsHint') }}</p>
          </div>

          <!-- 初始空状态 -->
          <div v-else-if="!searchStore.hasSearched && !searchStore.isExpanding && !searchStore.isSearching && !searchStore.totalFound" class="empty-state">
            <div class="empty-icon">📜</div>
            <p>{{ t('searchView.emptyHint') }}</p>
          </div>

          <!-- ① AI 关键词分析 -->
          <KeywordPanel :expansion="searchStore.expansion" />

          <!-- 统计栏 -->
          <div v-if="searchStore.totalFound > 0" class="stats-bar">
            <span v-html="t('searchView.statsHits', { count: searchStore.totalFound.toLocaleString() })"></span>
            <span>· {{ t('searchView.statsSentToAI', { count: Math.min(searchStore.topK, searchStore.totalFound) }) }}</span>
            <span v-if="searchStore.contextChars"> · {{ t('searchView.statsContext', { count: contextKw }) }}</span>
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
            @open-detail="openDetail"
          />
        </div>
      </div>

      <!-- ── 右侧对话栏 ── -->
      <ChatPanel
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

const { t } = useI18n()
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
let generation = 0

onUnmounted(() => searchAbort?.abort())

// 切换项目时自动清空并中断进行中的请求
watch(() => projectStore.currentProjectName, (n, o) => {
  if (n !== o && o !== undefined) {
    searchAbort?.abort()
    generation++
    searchStore.reset()
    searchHeaderRef.value?.loadAvailableFiles()
  }
})

const contextKw = computed(() => {
  const n = searchStore.contextChars
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`
  return n.toLocaleString()
})

const sourceRecords = computed<SearchRecord[]>(() => {
  const sent = searchStore.records.slice(0, searchStore.topK)
  const seen = new Set<string>()
  const result: SearchRecord[] = []
  for (const rec of sent) {
    const key = `${rec.source_file}::${rec.date || rec.year || rec.pub_year}`
    if (!seen.has(key)) { seen.add(key); result.push(rec) }
    if (result.length >= 20) break
  }
  return result
})

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
  if (!query || !projectStore.currentProjectName) return

  searchAbort?.abort()
  searchAbort = new AbortController()
  const signal = searchAbort.signal
  const gen = ++generation
  const active = () => gen === generation

  searchStore.reset()
  searchHeaderRef.value?.collapseAdvanced()

  // Step 1: AI 扩展
  searchStore.isExpanding = true
  try {
    const expansion = await api.post<any>('/api/search/expand', {
      query, language: searchStore.language,
      project_name: projectStore.currentProjectName,
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
      project_name: projectStore.currentProjectName,
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
      project_name: projectStore.currentProjectName,
      query, language: searchStore.language,
      expansion: searchStore.expansion,
      total_found: searchStore.totalFound,
      ai_output: '',
    })
    historyId = entry?.id || null
    window.dispatchEvent(new CustomEvent('history-updated'))
  } catch {}

  // Step 3: AI 流式摘录
  if (searchStore.searchId) {
    searchStore.isExtracting = true
    searchStore.aiOutput = ''
    extractionModelName.value = ''
    const sink = createThrottledSink(text => { searchStore.aiOutput += text })
    try {
      for await (const chunk of api.streamPost('/api/search/extract', {
        query, search_id: searchStore.searchId,
        language: searchStore.language,
        project_name: projectStore.currentProjectName,
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
      sink.flush()
      if (active()) {
        searchStore.isExtracting = false
        searchStore.extractionDone = true
        // 提取完成后更新历史记录的 ai_output
        if (historyId && searchStore.aiOutput) {
          try {
            await api.patch(`/api/history/${historyId}`, {
              ai_output: searchStore.aiOutput,
            })
            window.dispatchEvent(new CustomEvent('history-updated'))
          } catch {}
        }
      }
    }
  }
}

// ── AI 对话 ──
async function sendChat(text: string) {
  searchStore.chatMessages.push({ role: 'user', content: text })
  const messages = searchStore.chatMessages.map(m => ({ role: m.role, content: m.content }))
  searchStore.isChatStreaming = true
  streamingReply.value = ''
  const sink = createThrottledSink(chunk => {
    streamingReply.value += chunk
    chatPanelRef.value?.scrollToBottom()
  })
  let errored = false
  try {
    for await (const chunk of api.streamPost('/api/chat/stream', {
      messages, search_id: searchStore.searchId,
      language: searchStore.language,
      project_name: projectStore.currentProjectName,
    })) {
      if (chunk.text) sink.push(chunk.text)
      if (chunk.error) {
        errored = true
        ui.toast(chunk.error, 'error')
        break
      }
      if (chunk.done) break
    }
    sink.flush()
    if (streamingReply.value) {
      searchStore.chatMessages.push({ role: 'assistant', content: streamingReply.value })
    } else if (errored) {
      searchStore.chatMessages.push({ role: 'assistant', content: t('chat.failed') })
    }
  } catch {
    sink.flush()
    searchStore.chatMessages.push({ role: 'assistant', content: t('chat.failed') })
    ui.toast(t('chat.failed'), 'error')
  } finally {
    searchStore.isChatStreaming = false
    streamingReply.value = ''
    await nextTick()
    chatPanelRef.value?.scrollToBottom()
  }
}
</script>

<style scoped>
.search-view { flex: 1; display: flex; height: 100%; overflow: hidden; }
.left-column { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.results-scroll { flex: 1; overflow-y: auto; padding: 12px 20px 20px; display: flex; flex-direction: column; gap: 10px; }
.stats-bar { font-size: 12px; color: var(--text-muted); display: flex; gap: 8px; padding: 2px; }
.stats-bar b { color: var(--text); }
.empty-state, .loading-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-muted); gap: 10px; padding: 40px 0; }
.empty-state.full { width: 100%; height: 100%; }
.empty-icon { font-size: 48px; opacity: 0.4; }
.empty-icon.sm { font-size: 28px; }
.err-text { color: #e53e3e; }
.sub { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.spinner { font-size: 32px; opacity: 0.5; animation: spin 2s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.loading-state p { font-size: 14px; }
</style>
