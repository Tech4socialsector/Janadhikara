<template>
  <!-- A quiet always-visible "Online / Offline" indicator for the header. -->
  <span
    class="inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-medium"
    :class="online
      ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/30 dark:text-green-300'
      : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300'"
    :title="online ? 'Connected' : 'No internet connection - changes are saved on this device'"
  >
    <span class="relative flex h-2 w-2">
      <span v-if="online" class="net-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-60" />
      <span class="relative inline-flex h-2 w-2 rounded-full" :class="online ? 'bg-green-500' : 'bg-red-500'" />
    </span>
    <span :class="compact ? 'sr-only' : 'max-sm:sr-only'">{{ online ? t('Online') : t('Offline') }}</span>
    <span v-if="!online && pendingCount && !compact" class="rounded-full bg-red-600 px-1.5 text-2xs font-semibold text-white">{{ pendingCount }}</span>
  </span>
</template>

<script setup>
import { online } from '@/data/connection'
import { t } from '@/utils/translate'
import { pendingCount } from '@/data/offlineQueue'

defineProps({ compact: { type: Boolean, default: false } })
</script>

<style scoped>
.net-ping {
  animation: net-ping 2.4s ease-out infinite;
}
@keyframes net-ping {
  from { transform: scale(1); opacity: 0.6; }
  to { transform: scale(2.4); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .net-ping { animation: none; }
}
</style>
