import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { backendFetch, setBackendAuthToken } from '@/api/client'

export type BackendStage =
  | 'idle'
  | 'launching'
  | 'checking'
  | 'waiting'
  | 'reconnecting'
  | 'ready'
  | 'failed'

const HEALTH_URL = 'http://127.0.0.1:8765/api/health'
const INITIAL_MAX_ATTEMPTS = 75
const RECONNECT_MAX_ATTEMPTS = 30
const POLL_INTERVAL_MS = 1000
const HEALTH_TIMEOUT_MS = 2500
const HEALTHY_MONITOR_INTERVAL_MS = 5000

/**
 * Python sidecar 的生命周期状态。
 *
 * 打包版首次启动通常需要 20–40 秒。这里既负责首次就绪门控，也会在应用运行期间
 * 持续做健康检查：连续两次检查失败后进入重连，而不是让后续 API 请求静默失败。
 */
export const useBackendStore = defineStore('backend', () => {
  const ready = ref(false)
  const failed = ref(false)
  const hasConnected = ref(false)
  const stage = ref<BackendStage>('idle')
  const attempt = ref(0)
  const elapsedMs = ref(0)
  const lastError = ref('')

  const reconnecting = computed(() => hasConnected.value && !ready.value && !failed.value)
  const progress = computed(() => {
    if (ready.value) return 100
    // 进度以真实等待时间为基础；健康检查通过前不伪装成已完成。
    const expectedMs = reconnecting.value ? 15_000 : 40_000
    const ceiling = failed.value ? 94 : 92
    return Math.min(ceiling, 5 + (elapsedMs.value / expectedMs) * 87)
  })

  let generation = 0
  let activeRun = 0
  let connectionPromise: Promise<void> | null = null
  let elapsedTimer: number | null = null
  let monitorTimer: number | null = null
  let monitorFailures = 0
  let startedAt = 0
  let expectedInstanceToken: string | null = null
  let restartPromise: Promise<boolean> | null = null
  const pendingWaits = new Map<number, () => void>()

  const isTauri = () => '__TAURI_INTERNALS__' in window

  async function getExpectedInstanceToken(): Promise<string> {
    if (!isTauri()) return ''
    if (expectedInstanceToken !== null) return expectedInstanceToken
    try {
      const { invoke } = await import('@tauri-apps/api/core')
      expectedInstanceToken = await invoke<string>('backend_instance_token')
      setBackendAuthToken(expectedInstanceToken)
      return expectedInstanceToken
    } catch (error: any) {
      setBackendAuthToken('')
      lastError.value = error?.message || String(error || 'backend identity unavailable')
      return ''
    }
  }

  async function restartOwnedBackend(): Promise<boolean> {
    if (!isTauri()) return true
    if (restartPromise) return restartPromise
    expectedInstanceToken = null
    setBackendAuthToken('')
    const promise = (async () => {
      try {
        const { invoke } = await import('@tauri-apps/api/core')
        expectedInstanceToken = await invoke<string>('restart_backend')
        setBackendAuthToken(expectedInstanceToken)
        return true
      } catch (error: any) {
        lastError.value = error?.message || String(error || 'backend restart failed')
        return false
      }
    })()
    restartPromise = promise
    try {
      return await promise
    } finally {
      if (restartPromise === promise) restartPromise = null
    }
  }

  function clearTimer(timer: number | null) {
    if (timer !== null) window.clearTimeout(timer)
  }

  function stopElapsedClock() {
    if (elapsedTimer !== null) {
      window.clearInterval(elapsedTimer)
      elapsedTimer = null
    }
  }

  function startElapsedClock() {
    stopElapsedClock()
    startedAt = Date.now()
    elapsedMs.value = 0
    elapsedTimer = window.setInterval(() => {
      elapsedMs.value = Date.now() - startedAt
    }, 200)
  }

  async function checkHealth(): Promise<boolean> {
    const expectedToken = await getExpectedInstanceToken()
    if (isTauri() && !expectedToken) return false
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS)
    try {
      const response = await backendFetch(HEALTH_URL, {
        method: 'GET',
        cache: 'no-store',
        signal: controller.signal,
      })
      if (!response.ok) {
        lastError.value = `HTTP ${response.status}`
        return false
      }
      const payload = await response.json().catch(() => null)
      if (payload?.status !== 'ok') {
        lastError.value = 'invalid health response'
        return false
      }
      if (payload.version && payload.version !== __APP_VERSION__) {
        lastError.value = `backend ${payload.version} != app ${__APP_VERSION__}`
        return false
      }
      if (expectedToken && payload.instance_authenticated !== true) {
        lastError.value = 'backend instance authentication unavailable'
        return false
      }
      lastError.value = ''
      return true
    } catch (error: any) {
      lastError.value = error?.name === 'AbortError' ? 'timeout' : (error?.message || 'offline')
      return false
    } finally {
      window.clearTimeout(timeout)
    }
  }

  function wait(ms: number, run: number): Promise<void> {
    return new Promise(resolve => {
      const timer = window.setTimeout(() => {
        pendingWaits.delete(timer)
        void run
        resolve()
      }, ms)
      pendingWaits.set(timer, resolve)
    })
  }

  function cancelPendingWaits() {
    for (const [timer, resolve] of pendingWaits) {
      window.clearTimeout(timer)
      resolve()
    }
    pendingWaits.clear()
  }

  function scheduleMonitor(delay = HEALTHY_MONITOR_INTERVAL_MS) {
    clearTimer(monitorTimer)
    monitorTimer = window.setTimeout(runMonitor, delay)
  }

  async function runMonitor() {
    monitorTimer = null
    if (!ready.value || connectionPromise) return

    const ok = await checkHealth()
    if (!ready.value || connectionPromise) return

    if (ok) {
      monitorFailures = 0
      scheduleMonitor()
      return
    }

    monitorFailures += 1
    if (monitorFailures < 2) {
      scheduleMonitor(1500)
      return
    }

    ready.value = false
    // A transient timeout does not prove that the child exited: it may be
    // importing a large file, waiting on a slow disk, or briefly starved. Keep
    // polling the owned process and let the user explicitly restart only after
    // reconnection attempts are exhausted.
    void beginConnection('reconnect')
  }

  async function runConnection(
    run: number,
    mode: 'initial' | 'reconnect',
    maxAttempts: number,
    intervalMs: number,
  ) {
    clearTimer(monitorTimer)
    monitorTimer = null
    monitorFailures = 0
    ready.value = false
    failed.value = false
    lastError.value = ''
    attempt.value = 0
    stage.value = mode === 'reconnect' ? 'reconnecting' : 'launching'
    startElapsedClock()

    for (let i = 0; i < maxAttempts; i++) {
      if (run !== generation) return
      attempt.value = i + 1
      stage.value = mode === 'reconnect'
        ? 'reconnecting'
        : i === 0 ? 'launching' : 'checking'

      const ok = await checkHealth()
      if (run !== generation) return

      if (ok) {
        elapsedMs.value = Date.now() - startedAt
        stopElapsedClock()
        ready.value = true
        failed.value = false
        hasConnected.value = true
        stage.value = 'ready'
        window.dispatchEvent(new CustomEvent('backend-ready'))
        scheduleMonitor()
        return
      }

      stage.value = mode === 'reconnect' ? 'reconnecting' : 'waiting'
      if (i < maxAttempts - 1) await wait(intervalMs, run)
    }

    if (run !== generation) return
    elapsedMs.value = Date.now() - startedAt
    stopElapsedClock()
    failed.value = true
    ready.value = false
    stage.value = 'failed'
  }

  function beginConnection(
    mode: 'initial' | 'reconnect',
    maxAttempts = mode === 'initial' ? INITIAL_MAX_ATTEMPTS : RECONNECT_MAX_ATTEMPTS,
    intervalMs = POLL_INTERVAL_MS,
  ): Promise<void> {
    if (connectionPromise) return connectionPromise
    const run = ++generation
    activeRun = run
    const promise = runConnection(run, mode, maxAttempts, intervalMs)
    connectionPromise = promise
    promise.finally(() => {
      if (activeRun === run) {
        connectionPromise = null
        activeRun = 0
      }
    })
    return promise
  }

  function start(maxAttempts = INITIAL_MAX_ATTEMPTS, intervalMs = POLL_INTERVAL_MS) {
    if (ready.value) {
      scheduleMonitor()
      return Promise.resolve()
    }
    return beginConnection(hasConnected.value ? 'reconnect' : 'initial', maxAttempts, intervalMs)
  }

  async function retry() {
    generation += 1
    cancelPendingWaits()
    activeRun = 0
    connectionPromise = null
    failed.value = false
    stopElapsedClock()
    const restarted = await restartOwnedBackend()
    if (!restarted) {
      ready.value = false
      failed.value = true
      stage.value = 'failed'
      return
    }
    return beginConnection(hasConnected.value ? 'reconnect' : 'initial')
  }

  function stop() {
    generation += 1
    cancelPendingWaits()
    activeRun = 0
    connectionPromise = null
    clearTimer(monitorTimer)
    monitorTimer = null
    stopElapsedClock()
    setBackendAuthToken('')
  }

  return {
    ready,
    failed,
    hasConnected,
    stage,
    attempt,
    elapsedMs,
    lastError,
    reconnecting,
    progress,
    start,
    retry,
    stop,
  }
})
