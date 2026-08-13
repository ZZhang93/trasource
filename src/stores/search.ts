import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'

export interface SearchRecord {
  id: number
  source_file: string
  file_type: string
  doc_type: string
  year: string
  date: string
  page: string
  title: string
  author: string
  pub_year: string
  publisher: string
  chapter: string
  section: string
  page_num: string
  interviewee: string
  interview_date: string
  interview_location: string
  content: string
  content_truncated?: boolean
  relevance_score: number
}

export interface SearchExpansion {
  intent: string
  time_range: string | null
  terms: Record<string, number>
  success: boolean
  error?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export const useSearchStore = defineStore('search', () => {
  // 搜索输入
  const query = ref('')
  const language = ref<'zh' | 'en' | 'mixed'>('zh')
  const dateFrom = ref('')
  const dateTo = ref('')
  const fileFilter = ref<string[]>([])
  const storedTopK = Number(localStorage.getItem('trasource_search_top_k'))
  const topK = ref(
    Number.isFinite(storedTopK)
      ? Math.max(10, Math.min(200, Math.round(storedTopK / 10) * 10))
      : 50,
  )

  // 搜索结果
  // records 用 shallowRef：几千条记录不需要逐字段响应式代理，整体替换即可
  const expansion = ref<SearchExpansion | null>(null)
  const records = shallowRef<SearchRecord[]>([])
  const totalFound = ref(0)
  const searchId = ref('')        // 服务端 context 缓存句柄
  const contextChars = ref(0)
  // 后端实际写入 AI context 的记录 ID（顺序与 context 一致）。旧后端可不返回。
  const contextRecordIds = ref<number[]>([])
  const contextTruncated = ref(false)
  const aiOutput = ref('')

  // 所有异步搜索/历史恢复/对话共享的会话世代。任何新任务都会使旧回调失效。
  const sessionId = ref(0)
  const sessionProject = ref('')

  // 状态
  const isExpanding = ref(false)
  const isSearching = ref(false)
  const isExtracting = ref(false)
  const extractionDone = ref(false)
  const hasSearched = ref(false)   // 是否已执行过搜索（区分"初始"和"无结果"）
  const searchError = ref('')      // 搜索错误信息
  const extractError = ref('')     // AI 摘录错误信息（独立展示，不混入正文）

  // 对话
  const chatMessages = ref<ChatMessage[]>([])
  const isChatStreaming = ref(false)

  // 分页
  const currentPage = ref(1)
  const pageSize = ref(20)

  function beginSession(): number {
    sessionId.value += 1
    return sessionId.value
  }

  function reset(options: { clearFileFilter?: boolean } = {}) {
    expansion.value = null
    records.value = []
    totalFound.value = 0
    searchId.value = ''
    contextChars.value = 0
    contextRecordIds.value = []
    contextTruncated.value = false
    aiOutput.value = ''
    isExpanding.value = false
    isSearching.value = false
    isExtracting.value = false
    extractionDone.value = false
    chatMessages.value = []
    isChatStreaming.value = false
    currentPage.value = 1
    hasSearched.value = false
    searchError.value = ''
    extractError.value = ''
    if (options.clearFileFilter) fileFilter.value = []
  }

  function setProject(projectName: string): boolean {
    if (sessionProject.value === projectName) return false
    sessionProject.value = projectName
    beginSession()
    reset({ clearFileFilter: true })
    return true
  }

  return {
    query, language, dateFrom, dateTo, fileFilter, topK,
    expansion, records, totalFound, searchId, contextChars,
    contextRecordIds, contextTruncated, aiOutput,
    sessionId, sessionProject,
    isExpanding, isSearching, isExtracting, extractionDone,
    hasSearched, searchError, extractError,
    chatMessages, isChatStreaming,
    currentPage, pageSize,
    beginSession, reset, setProject,
  }
})
