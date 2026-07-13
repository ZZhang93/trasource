import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

/**
 * Markdown → 消毒后的 HTML。
 * 所有 v-html 渲染的 AI 输出/笔记内容都必须经过这里，防止 XSS。
 */
export function renderMarkdown(text: string): string {
  if (!text) return ''
  const html = marked.parse(text, { async: false }) as string
  return DOMPurify.sanitize(html)
}
