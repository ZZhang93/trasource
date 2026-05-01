<template>
  <div class="right-column">
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
          <div class="msg-text">{{ msg.content }}</div>
        </div>
      </div>
      <div v-if="isChatStreaming" class="chat-msg assistant">
        <span class="msg-avatar">🤖</span>
        <div class="msg-bubble">
          <div class="msg-text">{{ streamingReply }}<span class="cursor">▋</span></div>
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
.right-column { width: 300px; flex-shrink: 0; border-left: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
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
.chat-msg.user .msg-bubble { background: #EBF4FF; border-color: #bfdbfe; }
.msg-text { font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin: 0; font-family: var(--font-ui); }
.cursor { display: inline-block; animation: blink 0.8s infinite; color: var(--accent); }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
.chat-input-row { display: flex; flex-direction: column; gap: 6px; padding: 8px 10px 10px; border-top: 1px solid var(--border); flex-shrink: 0; }
.chat-textarea { resize: none; border: 1px solid var(--border); border-radius: var(--radius); padding: 7px 10px; font-size: 13px; font-family: var(--font-ui); color: var(--text); background: var(--bg); outline: none; line-height: 1.5; }
.chat-textarea:focus { border-color: var(--accent); }
.chat-textarea:disabled { opacity: 0.5; cursor: not-allowed; }
.send-btn { align-self: flex-end; }
</style>
