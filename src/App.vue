<template>
  <div
    v-if="backend.hasConnected"
    class="app-shell"
    :aria-hidden="!backend.ready"
    :inert="!backend.ready"
  >
    <Sidebar ref="sidebarRef" />
    <main class="main-content">
      <StatusBar />
      <div class="main-view">
        <router-view />
      </div>
    </main>

    <!-- 全局 Toast -->
    <div class="toast-stack" aria-live="polite">
      <div
        v-for="t in ui.toasts"
        :key="t.id"
        class="toast"
        :class="t.type"
        @click="ui.dismiss(t.id)"
      >
        <span class="toast-icon">{{ t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : 'ⓘ' }}</span>
        <span>{{ t.message }}</span>
      </div>
    </div>
  </div>
  <StartupScreen v-if="!backend.ready" :return-focus="startupReturnFocus" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import StatusBar from '@/components/layout/StatusBar.vue'
import StartupScreen from '@/components/layout/StartupScreen.vue'
import { useProjectStore } from '@/stores/project'
import { useBackendStore } from '@/stores/backend'
import { useUiStore } from '@/stores/ui'

const projectStore = useProjectStore()
const backend = useBackendStore()
const ui = useUiStore()
const router = useRouter()
const sidebarRef = ref<InstanceType<typeof Sidebar> | null>(null)
const startupReturnFocus = ref<HTMLElement | null>(null)

onMounted(() => {
  // 等后端健康检查通过后再拉项目列表（sidecar 冷启动需 20-40s，
  // 过早拉取会拉空列表，让用户误以为项目丢失）
  backend.start()
  window.addEventListener('keydown', handleKeydown)
})

watch(() => backend.ready, (r) => {
  if (r) {
    projectStore.fetchProjects()
  } else {
    // 在 app-shell 变为 inert 之前记住焦点，重连完成后准确返回原控件。
    const active = document.activeElement
    startupReturnFocus.value = active instanceof HTMLElement && active.closest('.app-shell')
      ? active
      : null
  }
}, { flush: 'sync' })

onUnmounted(() => {
  backend.stop()
  window.removeEventListener('keydown', handleKeydown)
})

const isMac = /mac/i.test(navigator.userAgent)

function handleKeydown(e: KeyboardEvent) {
  // 启动/重连层是模态界面。后端未就绪时不能让全局快捷键穿透到
  // inert 的应用壳（例如离线保存笔记或在后台切换路由）。
  if (!backend.ready) return

  const metaKey = isMac ? e.metaKey : e.ctrlKey
  const key = e.key.toLowerCase()

  // 跳过在输入框/textarea 中的事件（除了特定快捷键）
  const inInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
    (e.target as HTMLElement)?.tagName
  )

  // ⌘K 或 Ctrl+K — 聚焦搜索框，跳到搜索页
  if (metaKey && key === 'k') {
    e.preventDefault()
    router.push('/search')
    setTimeout(() => {
      const searchInput = document.querySelector('.search-input') as HTMLInputElement
      searchInput?.focus()
      searchInput?.select()
    }, 50)
    return
  }

  // ⌘S / Ctrl+S — 保存当前笔记（在输入框中也响应）
  if (metaKey && key === 's') {
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('save-note'))
    return
  }

  if (inInput) return

  // ⌘N / Ctrl+N — 新建笔记，跳到笔记页
  if (metaKey && key === 'n') {
    e.preventDefault()
    router.push('/notes')
    return
  }

  // ⌘, / Ctrl+, — 打开设置
  if (metaKey && e.key === ',') {
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('open-settings'))
    return
  }

  // Escape — 关闭任何打开的弹窗（通过 escape 事件传播）
  if (e.key === 'Escape') {
    window.dispatchEvent(new CustomEvent('close-dialogs'))
    return
  }
}
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg);
  color: var(--text);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.main-view {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

/* ── Toast ── */
.toast-stack {
  position: fixed;
  bottom: 36px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 3000;
}

.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  background: var(--text);
  color: var(--bg);
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  max-width: 360px;
  animation: toast-in 200ms ease-out;
}
.toast.success .toast-icon { color: #68d391; }
.toast.error .toast-icon { color: #fc8181; }
.toast.info .toast-icon { color: #90cdf4; }
.toast-icon { font-weight: 700; flex-shrink: 0; }

@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
