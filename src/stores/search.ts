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
  const topK = ref(50)

  // 搜索结果
  // records 用 shallowRef：几千条记录不需要逐字段响应式代理，整体替换即可
  const expansion = ref<SearchExpansion | null>(null)
  const records = shallowRef<SearchRecord[]>([])
  const totalFound = ref(0)
  const searchId = ref('')        // 服务端 context 缓存句柄
  const contextChars = ref(0)
  const aiOutput = ref('')

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

  function reset() {
    expansion.value = null
    records.value = []
    totalFound.value = 0
    searchId.value = ''
    contextChars.value = 0
    aiOutput.value = ''
    extractionDone.value = false
    chatMessages.value = []
    currentPage.value = 1
    hasSearched.value = false
    searchError.value = ''
    extractError.value = ''
  }

  return {
    query, language, dateFrom, dateTo, fileFilter, topK,
    expansion, records, totalFound, searchId, contextChars, aiOutput,
    isExpanding, isSearching, isExtracting, extractionDone,
    hasSearched, searchError, extractError,
    chatMessages, isChatStreaming,
    currentPage, pageSize,
    reset,
  }
})
