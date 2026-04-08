import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface SearchRecord {
  id: string | number
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
  const expansion = ref<SearchExpansion | null>(null)
  const records = ref<SearchRecord[]>([])
  const totalFound = ref(0)
  const contextText = ref('')
  const aiOutput = ref('')

  // 状态
  const isExpanding = ref(false)
  const isSearching = ref(false)
  const isExtracting = ref(false)
  const extractionDone = ref(false)
  const hasSearched = ref(false)   // 是否已执行过搜索（区分"初始"和"无结果"）
  const searchError = ref('')      // 搜索错误信息

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
    contextText.value = ''
    aiOutput.value = ''
    extractionDone.value = false
    chatMessages.value = []
    currentPage.value = 1
    hasSearched.value = false
    searchError.value = ''
  }

  return {
    query, language, dateFrom, dateTo, fileFilter, topK,
    expansion, records, totalFound, contextText, aiOutput,
    isExpanding, isSearching, isExtracting, extractionDone,
    hasSearched, searchError,
    chatMessages, isChatStreaming,
    currentPage, pageSize,
    reset,
  }
})
