<template>
  <div class="app-shell">
    <Sidebar ref="sidebarRef" />
    <main class="main-content">
      <StatusBar />
      <div class="main-view">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import StatusBar from '@/components/layout/StatusBar.vue'
import { useProjectStore } from '@/stores/project'
import { useSearchStore } from '@/stores/search'

const projectStore = useProjectStore()
const searchStore = useSearchStore()
const router = useRouter()
const sidebarRef = ref<InstanceType<typeof Sidebar> | null>(null)

onMounted(async () => {
  await projectStore.fetchProjects()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function handleKeydown(e: KeyboardEvent) {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const metaKey = isMac ? e.metaKey : e.ctrlKey

  // 跳过在输入框/textarea 中的事件（除了特定快捷键）
  const inInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
    (e.target as HTMLElement)?.tagName
  )

  // ⌘K 或 Ctrl+K — 聚焦搜索框，跳到搜索页
  if (metaKey && e.key === 'k') {
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
  if (metaKey && e.key === 's') {
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('save-note'))
    return
  }

  if (inInput) return

  // ⌘N / Ctrl+N — 新建笔记，跳到笔记页
  if (metaKey && e.key === 'n') {
    e.preventDefault()
    router.push('/notes')
    return
  }

  // ⌘, / Ctrl+, — 打开设置
  if (metaKey && e.key === ',') {
    e.preventDefault()
    // Emit custom event that Sidebar listens to
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
</style>
