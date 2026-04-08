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
            <span v-if="searchStore.contextText"> · {{ t('searchView.statsContext', { count: contextKw }) }}</span>
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
import { ref, computed, nextTick, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useSearchStore, type SearchRecord } from '@/stores/search'
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

const searchHeaderRef = ref<InstanceType<typeof SearchHeader> | null>(null)
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)
const detailRecord = ref<SearchRecord | null>(null)
const streamingReply = ref('')
const extractionModelName = ref('')

// 切换项目时自动清空
watch(() => projectStore.currentProjectName, (n, o) => {
  if (n !== o && o !== undefined) {
    searchStore.reset()
    searchHeaderRef.value?.loadAvailableFiles()
  }
})

const contextKw = computed(() => {
  const n = searchStore.contextText.length
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
function onCreateNote() { detailRecord.value = null }

// ── 主搜索流程 ──
async function handleSearch() {
  const query = searchStore.query.trim()
  if (!query || !projectStore.currentProjectName) return

  searchStore.reset()
  searchHeaderRef.value?.collapseAdvanced()

  // Step 1: AI 扩展
  searchStore.isExpanding = true
  try {
    const expansion = await api.post<any>('/api/search/expand', {
      query, language: searchStore.language,
      project_name: projectStore.currentProjectName,
    })
    searchStore.expansion = expansion
  } catch (e) {
    console.warn('AI扩展失败:', e)
    searchStore.expansion = { intent: '', time_range: null, terms: {}, success: false }
  } finally {
    searchStore.isExpanding = false
  }

  // Step 2: BM25 搜索
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
    })
    searchStore.records = result.records || []
    searchStore.totalFound = result.total_found || searchStore.records.length || 0
    searchStore.contextText = result.context || ''
    searchStore.hasSearched = true
  } catch (e: any) {
    searchStore.searchError = e?.message || t('searchView.searchFailed')
    searchStore.hasSearched = true
  } finally {
    searchStore.isSearching = false
  }

  // 立即保存历史记录（BM25 完成后就保存，不等 AI 提取）
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
  if (searchStore.contextText) {
    searchStore.isExtracting = true
    searchStore.aiOutput = ''
    extractionModelName.value = ''
    try {
      for await (const chunk of api.streamPost('/api/search/extract', {
        query, context: searchStore.contextText,
        language: searchStore.language,
        project_name: projectStore.currentProjectName,
      })) {
        if (chunk.model !== undefined) {
          extractionModelName.value = chunk.model || ''
          continue
        }
        if (chunk.text) searchStore.aiOutput += chunk.text
        if (chunk.done || chunk.error) break
      }
    } catch {
      searchStore.aiOutput += '\n\n' + t('searchView.extractionFailed')
    } finally {
      searchStore.isExtracting = false
      searchStore.extractionDone = true
      // 提取完成后更新历史记录的 ai_output
      if (historyId) {
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

// ── AI 对话 ──
async function sendChat(text: string) {
  searchStore.chatMessages.push({ role: 'user', content: text })
  const messages = searchStore.chatMessages.map(m => ({ role: m.role, content: m.content }))
  searchStore.isChatStreaming = true
  streamingReply.value = ''
  try {
    for await (const chunk of api.streamPost('/api/chat/stream', {
      messages, context: searchStore.contextText,
      language: searchStore.language,
      project_name: projectStore.currentProjectName,
    })) {
      if (chunk.text) {
        streamingReply.value += chunk.text
        chatPanelRef.value?.scrollToBottom()
      }
      if (chunk.done || chunk.error) break
    }
    searchStore.chatMessages.push({ role: 'assistant', content: streamingReply.value })
  } catch {
    searchStore.chatMessages.push({ role: 'assistant', content: t('chat.failed') })
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
