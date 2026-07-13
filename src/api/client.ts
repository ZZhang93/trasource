/**
 * API Client — 封装所有对 Python FastAPI 后端的调用
 * 开发模式：后端运行在 localhost:8765
 * 生产模式（Tauri）：后端作为 sidecar，同样监听 localhost:8765
 */

const BASE_URL = 'http://127.0.0.1:8765'

class ApiClient {
  private base: string

  constructor(base: string) {
    this.base = base
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    const url = `${this.base}${path}`
    const opts: RequestInit = {
      method,
      headers: { 'Content-Type': 'application/json' },
      signal,
    }
    if (body !== undefined) {
      opts.body = JSON.stringify(body)
    }
    const res = await fetch(url, opts)
    if (!res.ok) {
      const err = await res.text()
      throw new Error(`API ${method} ${path} failed (${res.status}): ${err}`)
    }
    return res.json()
  }

  get<T = unknown>(path: string) {
    return this.request<T>('GET', path)
  }

  post<T = unknown>(path: string, body?: unknown, signal?: AbortSignal) {
    return this.request<T>('POST', path, body, signal)
  }

  put<T = unknown>(path: string, body?: unknown) {
    return this.request<T>('PUT', path, body)
  }

  delete<T = unknown>(path: string) {
    return this.request<T>('DELETE', path)
  }

  patch<T = unknown>(path: string, body?: unknown) {
    return this.request<T>('PATCH', path, body)
  }

  /**
   * SSE 流式接口：返回 EventSource
   * 用法：
   *   const es = api.stream('/api/search/extract?query=...')
   *   es.onmessage = (e) => { const d = JSON.parse(e.data); ... }
   *   es.onerror   = (e) => { es.close() }
   */
  stream(path: string): EventSource {
    return new EventSource(`${this.base}${path}`)
  }

  /**
   * POST + SSE：先 POST 请求参数，然后接收 SSE 流
   * 用 fetch + ReadableStream 实现（EventSource 不支持 POST）
   * 传入 AbortSignal 可随时取消（新搜索发起时中断旧流）
   */
  async *streamPost(
    path: string,
    body: unknown,
    signal?: AbortSignal,
  ): AsyncGenerator<{ text?: string; done?: boolean; error?: string; stale?: boolean; model?: string }> {
    const res = await fetch(`${this.base}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal,
    })

    if (!res.ok) {
      const err = await res.text()
      throw new Error(`Stream POST ${path} failed (${res.status}): ${err}`)
    }

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') return
          try {
            yield JSON.parse(data)
          } catch {
            // ignore malformed lines
          }
        }
      }
    }
  }
}

export const api = new ApiClient(BASE_URL)
