<template>
  <div class="history-view">
    <div class="empty-state">
      <div class="empty-icon">🕐</div>
      <p>{{ t('history.placeholder') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '@/i18n'

const { t } = useI18n()
</script>

<style scoped>
.history-view {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; height: 100%;
}
.empty-state {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: var(--text-muted); gap: 12px;
}
.empty-icon { font-size: 48px; opacity: 0.4; }
</style>
