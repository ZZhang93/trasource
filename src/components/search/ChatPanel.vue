<template>
  <div class="right-column" :style="{ width: panelWidth + 'px' }">
    <div class="resize-handle" @pointerdown="startResize" />
    <div class="chat-panel-header">
      <span>{{ t('chat.title') }}</span>
      <button
        v-if="aiOutput && extractionDone"
        class="quote-btn"
        @click="quoteToChat"
      >{{ t('chat.quoteExtraction') }}</button>
    </div>

    <div class="chat-messages" ref="chatEl">
      <div v-if="!extractionDone && chatMessages.length === 0" class="chat-waiting">
        <p>{{ t('chat.waitingHint') }}</p>
      </div>
      <div
        v-for="(msg, i) in chatMessages"
        :key="i"
        class="chat-msg"
        :class="msg.role"
      >
        <span class="msg-avatar">{{ msg.role === 'user' ? '🧑' : '🤖' }}</span>
        <div class="msg-bubble">
          <div v-if="msg.role === 'user'" class="msg-text">{{ msg.content }}</div>
          <div v-else class="msg-text msg-md" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
      <div v-if="isChatStreaming" class="chat-msg assistant">
        <span class="msg-avatar">🤖</span>
        <div class="msg-bubble">
          <div class="msg-text msg-md"><span v-html="renderMarkdown(streamingReply)"></span><span class="cursor">▋</span></div>
        </div>
      </div>
    </div>

    <div class="chat-input-row">
      <textarea
        v-model="chatInput"
        class="chat-textarea"
        :placeholder="t('chat.placeholder')"
        rows="3"
        :disabled="!extractionDone"
        @keydown.enter.exact.prevent="sendChat"
      />
      <button
        class="btn-primary send-btn"
        @click="sendChat"
        :disabled="!chatInput.trim() || isChatStreaming || !extractionDone"
      >{{ t('chat.send') }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import { useI18n } from '@/i18n'
const { t } = useI18n()

const props = defineProps<{
  chatMessages: { role: string; content: string }[]
  isChatStreaming: boolean
  extractionDone: boolean
  aiOutput: string
  streamingReply: string
}>()

const emit = defineEmits<{
  'send-message': [text: string]
}>()

const chatInput = ref('')
const chatEl = ref<HTMLElement | null>(null)

// ── 可拖拽调宽（持久化到 localStorage） ──
const WIDTH_KEY = 'trasource_chat_width'
const panelWidth = ref(Number(localStorage.getItem(WIDTH_KEY)) || 300)

function startResize(e: PointerEvent) {
  const startX = e.clientX
  const startWidth = panelWidth.value
  const onMove = (ev: PointerEvent) => {
    panelWidth.value = Math.min(560, Math.max(240, startWidth + (startX - ev.clientX)))
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    localStorage.setItem(WIDTH_KEY, String(panelWidth.value))
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

function quoteToChat() {
  if (!props.aiOutput) return
  const excerpt = props.aiOutput.length > 500
    ? props.aiOutput.slice(0, 500) + '…'
    : props.aiOutput
  chatInput.value = `【引用AI摘录】\n${excerpt}\n\n请问：`
  nextTick(() => {
    const ta = document.querySelector('.chat-textarea') as HTMLTextAreaElement
    if (ta) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length) }
  })
}

function sendChat() {
  const text = chatInput.value.trim()
  if (!text || props.isChatStreaming) return
  chatInput.value = ''
  emit('send-message', text)
}

function scrollToBottom() {
  nextTick(() => {
    if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
  })
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.right-column { flex-shrink: 0; border-left: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; position: relative; }
.resize-handle { position: absolute; left: 0; top: 0; bottom: 0; width: 5px; cursor: col-resize; z-index: 10; }
.resize-handle:hover { background: var(--accent); opacity: 0.35; }
.chat-panel-header { display: flex; align-items: center; justify-content: space-between; padding: 9px 12px; background: var(--sidebar-bg); border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 500; flex-shrink: 0; }
.quote-btn { font-size: 11px; padding: 2px 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); color: var(--text-muted); cursor: pointer; }
.quote-btn:hover { border-color: var(--accent); color: var(--accent); }
.chat-messages { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
.chat-waiting { flex: 1; display: flex; align-items: center; justify-content: center; }
.chat-waiting p { font-size: 12px; color: var(--text-muted); text-align: center; }
.chat-msg { display: flex; gap: 6px; align-items: flex-start; }
.chat-msg.user { flex-direction: row-reverse; }
.msg-avatar { font-size: 14px; flex-shrink: 0; margin-top: 2px; }
.msg-bubble { max-width: 88%; padding: 7px 10px; border-radius: var(--radius-md); background: var(--sidebar-bg); border: 1px solid var(--border); }
.chat-msg.user .msg-bubble { background: var(--accent-soft); border-color: #bfdbfe; }
.msg-text { font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin: 0; font-family: var(--font-ui); }
.msg-md { white-space: normal; }
.msg-md :deep(p) { margin: 0 0 8px; }
.msg-md :deep(p:last-child) { margin-bottom: 0; }
.msg-md :deep(ul), .msg-md :deep(ol) { padding-left: 18px; margin: 0 0 8px; }
.msg-md :deep(li) { margin-bottom: 3px; }
.msg-md :deep(code) { font-family: var(--font-mono); font-size: 11px; background: var(--hover-bg); padding: 1px 4px; border-radius: 3px; }
.msg-md :deep(pre) { background: var(--sidebar-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px; overflow-x: auto; margin: 8px 0; }
.msg-md :deep(blockquote) { border-left: 2px solid var(--accent); padding: 2px 8px; margin: 6px 0; color: var(--text-muted); }
.msg-md :deep(h1), .msg-md :deep(h2), .msg-md :deep(h3) { font-size: 13px; font-weight: 700; margin: 8px 0 4px; }
.cursor { display: inline-block; animation: blink 0.8s infinite; color: var(--accent); }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
.chat-input-row { display: flex; flex-direction: column; gap: 6px; padding: 8px 10px 10px; border-top: 1px solid var(--border); flex-shrink: 0; }
.chat-textarea { resize: none; border: 1px solid var(--border); border-radius: var(--radius); padding: 7px 10px; font-size: 13px; font-family: var(--font-ui); color: var(--text); background: var(--bg); outline: none; line-height: 1.5; }
.chat-textarea:focus { border-color: var(--accent); }
.chat-textarea:disabled { opacity: 0.5; cursor: not-allowed; }
.send-btn { align-self: flex-end; }
</style>
