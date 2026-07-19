import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'

/**
 * 后端就绪状态。
 * 打包版的 Python sidecar 冷启动需要 20-40 秒，期间任何 API 调用都会失败。
 * 所有「启动时拉数据」的逻辑都必须等 ready 为 true 之后再执行，
 * 否则会出现项目列表拉空 → 用户误以为项目丢失的问题。
 */
export const useBackendStore = defineStore('backend', () => {
  const ready = ref(false)
  const failed = ref(false)
  let started = false

  async function start(maxAttempts = 120, intervalMs = 1000) {
    if (started) return
    started = true
    for (let i = 0; i < maxAttempts; i++) {
      try {
        await api.get('/api/health')
        ready.value = true
        window.dispatchEvent(new CustomEvent('backend-ready'))
        return
      } catch {
        await new Promise(r => setTimeout(r, intervalMs))
      }
    }
    failed.value = true
  }

  return { ready, failed, start }
})
