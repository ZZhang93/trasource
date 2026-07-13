import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'info'
  message: string
}

let nextId = 1

export const useUiStore = defineStore('ui', () => {
  const toasts = ref<Toast[]>([])

  function toast(message: string, type: Toast['type'] = 'info', durationMs = 3500) {
    const id = nextId++
    toasts.value.push({ id, type, message })
    setTimeout(() => dismiss(id), durationMs)
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { toasts, toast, dismiss }
})
