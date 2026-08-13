import type { SearchRecord } from '@/stores/search'

export interface ExtractionEntry {
  body: string
  citation: string
  record: SearchRecord | null
}

export interface CitationRecordId {
  present: boolean
  id: number | null
}

/**
 * 读取 AI 引用里的稳定记录 ID。
 * `present` 与 `id` 分开表达：如果模型输出了标签但值无效，调用方必须视为
 * 不可匹配，不能再降级到相似度猜测。
 */
export function parseCitationRecordId(citation: string): CitationRecordId {
  const label = /(?:记录\s*ID|Record\s*ID)\s*[：:]/i
  if (!label.test(citation)) return { present: false, id: null }
  const match = citation.match(/(?:记录\s*ID|Record\s*ID)\s*[：:]\s*(\d+)/i)
  if (!match) return { present: true, id: null }
  const id = Number(match[1])
  return { present: true, id: Number.isSafeInteger(id) ? id : null }
}

function normalise(value: unknown): string {
  return String(value || '')
    .toLocaleLowerCase()
    .replace(/[\s\p{P}\p{S}]+/gu, '')
}

function citationCandidates(record: SearchRecord): string[] {
  return [
    record.source_file,
    record.date,
    record.year,
    record.pub_year,
    record.page,
    record.page_num,
    record.title,
    record.author,
    record.publisher,
    record.chapter,
    record.section,
    record.interviewee,
    record.interview_date,
    record.interview_location,
  ].filter(Boolean)
}

/**
 * 新版后端把 context_record_ids 作为 sourceRecords 白名单传入；引用包含 ID 时只做
 * 白名单内精确匹配。无 ID 的旧历史/旧后端结果才使用保守的元数据相似度回退。
 */
export function matchExtractionRecord(
  body: string,
  citation: string,
  sourceRecords: SearchRecord[],
): SearchRecord | null {
  const citationId = parseCitationRecordId(citation)
  if (citationId.present) {
    if (citationId.id === null) return null
    return sourceRecords.find(record => Number(record.id) === citationId.id) || null
  }

  const haystack = normalise(`${citation} ${body}`)
  if (!haystack) return null

  const scored = sourceRecords.map(record => {
    let score = 0
    const citationText = normalise(citation)
    for (const candidate of citationCandidates(record)) {
      const token = normalise(candidate)
      if (!token || token.length < 2) continue
      if (citationText.includes(token)) score += token.length >= 6 ? 5 : 3
      else if (haystack.includes(token)) score += 1
    }

    const excerpt = normalise(body).slice(0, 36)
    const recordText = normalise(record.content)
    if (excerpt.length >= 10 && recordText.includes(excerpt)) score += 12
    return { record, score }
  }).sort((a, b) => b.score - a.score)

  if (!scored.length || scored[0].score < 5) return null
  // 同分意味着来源不唯一：宁可标为未定位，也不把摘录链接到错误原文。
  if (scored[1] && scored[1].score === scored[0].score) return null
  return scored[0].record
}

function stripMarkdownWrapper(value: string): string {
  return value
    .trim()
    .replace(/^[-*+]\s+/, '')
    .replace(/^\d+[.)、]\s*/, '')
}

export function parseExtractionEntries(
  output: string,
  sourceRecords: SearchRecord[],
): ExtractionEntry[] {
  const text = output.replace(/\r\n/g, '\n').trim()
  if (!text) return []

  const lines = text.split(/\n+/).map(stripMarkdownWrapper).filter(Boolean)
  const parsed: Array<{ body: string; citation: string }> = []
  const citationPattern = /^(.*?)\s*[—━─-]{2,}\s*(?:\*\*)?\s*(\[(?:引用|Citation)\s*[：:]?[\s\S]*?\])\s*(?:\*\*)?\s*$/i

  for (const line of lines) {
    const match = line.match(citationPattern)
    if (match) {
      const body = match[1].trim()
      const previous = parsed[parsed.length - 1]
      if (!body && previous && !previous.citation) {
        previous.citation = match[2].trim()
      } else {
        parsed.push({ body, citation: match[2].trim() })
      }
      continue
    }

    const standaloneCitation = line.match(/^(.*?)(?:\*\*)?(\[(?:引用|Citation)\s*[：:]?[\s\S]*?\])(?:\*\*)?$/i)
    if (standaloneCitation) {
      const leadingBody = standaloneCitation[1]
        .replace(/[—━─-]{2,}\s*$/, '')
        .trim()
      const previous = parsed[parsed.length - 1]
      if (previous && !previous.citation) {
        if (leadingBody) previous.body += `\n${leadingBody}`
        previous.citation = standaloneCitation[2].trim()
      } else {
        parsed.push({ body: leadingBody, citation: standaloneCitation[2].trim() })
      }
    } else if (parsed.length && !parsed[parsed.length - 1].citation) {
      parsed[parsed.length - 1].body += `\n${line}`
    } else {
      parsed.push({ body: line, citation: '' })
    }
  }

  return parsed
    .filter(item => item.body || item.citation)
    .map(item => ({
      ...item,
      record: matchExtractionRecord(item.body, item.citation, sourceRecords),
    }))
}
