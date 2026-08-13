<template>
  <div
    ref="screenEl"
    class="startup-screen"
    role="dialog"
    aria-modal="true"
    aria-labelledby="startup-title"
    aria-describedby="startup-description"
    tabindex="-1"
    @keydown="handleKeydown"
  >
    <div class="startup-card" :class="{ failed: backend.failed }">
      <div class="brand-mark" aria-hidden="true">
        <span class="brand-ripple ripple-one"></span>
        <span class="brand-ripple ripple-two"></span>
        <span class="brand-core">问</span>
      </div>

      <div class="startup-copy">
        <p class="eyebrow">{{ t('startup.eyebrow') }}</p>
        <h1 id="startup-title">{{ title }}</h1>
        <p id="startup-description" class="description">{{ description }}</p>
      </div>

      <template v-if="!backend.failed">
        <div class="progress-block">
          <div class="progress-meta">
            <span class="stage-label" aria-live="polite">
              <span class="live-dot" aria-hidden="true"></span>
              {{ stageLabel }}
            </span>
            <span class="elapsed" aria-hidden="true">{{ elapsedLabel }}</span>
          </div>
          <div
            class="progress-track"
            role="progressbar"
            :aria-label="stageLabel"
            :aria-valuenow="Math.round(backend.progress)"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div class="progress-fill" :style="{ width: `${backend.progress}%` }">
              <span class="progress-shine"></span>
            </div>
          </div>
          <p v-if="!backend.hasConnected" class="first-start-hint">
            {{ t('startup.firstStartHint') }}
          </p>
        </div>
      </template>

      <div v-else class="failure-actions">
        <p class="failure-hint" role="alert">{{ t('startup.failedHint') }}</p>
        <button ref="retryButtonEl" class="btn-primary retry-btn" @click="backend.retry">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M13.2 5.2A5.6 5.6 0 1 0 13.5 10M13.2 2.5v2.8h-2.8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ t('startup.retry') }}
        </button>
      </div>

      <p class="local-note">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M3 7V5.5a5 5 0 0 1 10 0V7M2.5 7h11v6.5h-11z" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round"/>
        </svg>
        {{ t('startup.localNote') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useBackendStore } from '@/stores/backend'
import { useI18n } from '@/i18n'

const backend = useBackendStore()
const { t } = useI18n()
const props = defineProps<{ returnFocus?: HTMLElement | null }>()
const screenEl = ref<HTMLElement | null>(null)
const retryButtonEl = ref<HTMLButtonElement | null>(null)
let restoreTarget: HTMLElement | null = null

function focusableElements(): HTMLElement[] {
  if (!screenEl.value) return []
  return Array.from(screenEl.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )).filter(element => !element.hasAttribute('hidden'))
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  const focusable = focusableElements()
  if (!focusable.length) {
    event.preventDefault()
    screenEl.value?.focus()
    return
  }

  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  const active = document.activeElement
  if (event.shiftKey && (active === first || active === screenEl.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && (active === last || active === screenEl.value)) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  restoreTarget = props.returnFocus
    || (document.activeElement instanceof HTMLElement ? document.activeElement : null)
  void nextTick(() => screenEl.value?.focus())
})

watch(() => backend.failed, failed => {
  void nextTick(() => {
    if (failed) retryButtonEl.value?.focus()
    else screenEl.value?.focus()
  })
})

onUnmounted(() => {
  const target = restoreTarget
  void nextTick(() => {
    if (target?.isConnected) target.focus()
  })
})

const title = computed(() => {
  if (backend.failed) return t('startup.failedTitle')
  if (backend.hasConnected) return t('startup.reconnectingTitle')
  return t('startup.title')
})

const description = computed(() =>
  backend.hasConnected
    ? t('startup.reconnectingDescription')
    : t('startup.description')
)

const stageLabel = computed(() => {
  if (backend.reconnecting) {
    return t('startup.stageReconnecting', { attempt: backend.attempt })
  }
  if (backend.stage === 'launching') return t('startup.stageLaunching')
  if (backend.stage === 'checking' || backend.stage === 'waiting') {
    return t('startup.stageChecking', { attempt: backend.attempt })
  }
  return t('startup.stagePreparing')
})

const elapsedLabel = computed(() =>
  t('startup.elapsed', { seconds: Math.max(0, Math.floor(backend.elapsedMs / 1000)) })
)
</script>

<style scoped>
.startup-screen {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: grid;
  place-items: center;
  overflow: auto;
  padding: 32px;
  background:
    radial-gradient(circle at 50% 42%, rgba(47,107,255,0.08), transparent 34%),
    linear-gradient(160deg, #fbfcff 0%, var(--surface-2) 100%);
  color: var(--text);
}

.startup-screen::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.32;
  background-image: linear-gradient(rgba(23,24,28,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(23,24,28,0.025) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(circle at center, #000 0%, transparent 68%);
}

.startup-card {
  position: relative;
  width: min(460px, 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.brand-mark {
  position: relative;
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  margin-bottom: 26px;
}

.brand-core {
  position: relative;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border: 1px solid var(--accent-line);
  border-radius: 17px;
  background: var(--bg);
  box-shadow: 0 12px 34px rgba(47,107,255,0.14), var(--shadow-sm);
  color: var(--accent);
  font-size: 22px;
  font-weight: 650;
}

.brand-ripple {
  position: absolute;
  inset: 5px;
  border: 1px solid rgba(47,107,255,0.2);
  border-radius: 22px;
  animation: ripple 2.8s ease-out infinite;
}
.ripple-two { animation-delay: 1.4s; }
.startup-card.failed .brand-ripple { animation: none; border-color: rgba(220,58,52,0.18); }
.startup-card.failed .brand-core { color: var(--danger); border-color: rgba(220,58,52,0.25); box-shadow: 0 12px 34px rgba(220,58,52,0.09); }

@keyframes ripple {
  0% { opacity: 0.7; transform: scale(0.78); }
  75%, 100% { opacity: 0; transform: scale(1.28); }
}

@media (prefers-reduced-motion: reduce) {
  .brand-ripple, .live-dot, .progress-shine { animation: none !important; }
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 10px;
  font-size: 23px;
  line-height: 1.3;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.description {
  max-width: 390px;
  margin: 0;
  color: var(--text-2);
  font-size: 13.5px;
  line-height: 1.75;
}

.progress-block {
  width: 100%;
  margin-top: 32px;
  padding: 15px 17px 14px;
  border: 1px solid rgba(214,217,222,0.82);
  border-radius: var(--radius-lg);
  background: rgba(255,255,255,0.78);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(10px);
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.stage-label {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  color: var(--text-2);
  font-size: 12px;
  text-align: left;
}

.live-dot {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  margin-right: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(47,107,255,0.1);
}

.elapsed {
  flex-shrink: 0;
  color: var(--text-2);
  font-family: var(--font-mono);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.progress-track {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--surface-3);
}

.progress-fill {
  position: relative;
  height: 100%;
  min-width: 5px;
  overflow: hidden;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), #5a8aff);
  transition: width 350ms cubic-bezier(0.2, 0, 0, 1);
}

.progress-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.55) 48%, transparent 100%);
  transform: translateX(-100%);
  animation: shine 1.8s ease-in-out infinite;
}

@keyframes shine { to { transform: translateX(100%); } }

.first-start-hint {
  margin: 10px 0 0;
  color: var(--text-2);
  font-size: 11.5px;
  line-height: 1.55;
}

.failure-actions {
  width: 100%;
  margin-top: 28px;
  padding: 16px;
  border: 1px solid rgba(220,58,52,0.2);
  border-radius: var(--radius-lg);
  background: rgba(254,241,240,0.72);
}

.failure-hint {
  margin: 0 0 13px;
  color: var(--text-2);
  font-size: 12.5px;
  line-height: 1.65;
}

.retry-btn { margin: 0 auto; }

.local-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 18px 0 0;
  color: var(--text-2);
  font-size: 11px;
}

@media (max-width: 520px) {
  .startup-screen { padding: 24px; }
  h1 { font-size: 21px; }
  .progress-block { padding-inline: 14px; }
}
</style>
