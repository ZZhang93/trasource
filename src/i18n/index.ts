import { reactive, computed } from 'vue'
import zh from './zh'
import en from './en'

const messages: Record<string, Record<string, string>> = { zh, en }

const state = reactive({
  locale: localStorage.getItem('trasource_locale') || 'zh',
})

/**
 * 翻译函数。支持简单插值：t('key', { count: 5 }) 会替换 {count}
 */
export function t(key: string, params?: Record<string, string | number>): string {
  let text = messages[state.locale]?.[key] ?? messages['zh'][key] ?? key
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
    }
  }
  return text
}

export function setLocale(loc: string) {
  state.locale = loc
  localStorage.setItem('trasource_locale', loc)
}

export function getLocale(): string {
  return state.locale
}

export function useI18n() {
  return {
    t,
    locale: computed(() => state.locale),
    setLocale,
  }
}
