<template>
  <!-- Slides in when the connection drops, and again - in green - when it is back. -->
  <Transition name="conn">
    <div
      v-if="!online && !dismissed && route.name !== 'SyncData'"
      key="offline"
      role="status"
      class="conn-bar mb-3 flex items-center gap-3 rounded-xl border border-outline-gray-2 bg-surface-gray-7 px-3.5 py-2.5 text-ink-white shadow-sm"
    >
      <span class="conn-pulse-off relative flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-white/10">
        <FeatherIcon name="wifi-off" class="h-4 w-4" />
      </span>
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold leading-tight">You're offline</p>
        <p class="text-xs leading-snug text-white/70">
          Everything you save is kept on this device<template v-if="pendingCount"> · {{ pendingCount }} waiting</template>.
        </p>
      </div>
      <router-link :to="{ name: 'SyncData' }" class="flex-shrink-0 rounded-lg bg-white/15 px-2.5 py-1.5 text-xs font-medium hover:bg-white/25">
        Sync Data
      </router-link>
      <button type="button" class="flex-shrink-0 rounded-md p-1 text-white/70 hover:bg-white/15 hover:text-white" aria-label="Dismiss" title="Dismiss" @click="dismissed = true">
        <FeatherIcon name="x" class="h-4 w-4" />
      </button>
    </div>

    <div
      v-else-if="online && justReconnected && !dismissed"
      key="online"
      role="status"
      class="conn-bar mb-3 flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 px-3.5 py-2.5 text-green-900 shadow-sm dark:border-green-800 dark:bg-green-900/30 dark:text-green-100"
    >
      <span class="conn-pop flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-green-500 text-white">
        <FeatherIcon name="wifi" class="h-4 w-4" />
      </span>
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold leading-tight">Back online</p>
        <p class="text-xs leading-snug opacity-80">
          <template v-if="pendingCount">{{ pendingCount }} saved on this device {{ pendingCount === 1 ? 'is' : 'are' }} waiting to upload.</template>
          <template v-else>Everything is up to date.</template>
        </p>
      </div>
      <router-link
        v-if="pendingCount"
        :to="{ name: 'SyncData' }"
        class="flex-shrink-0 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-green-700"
      >
        Sync now
      </router-link>
      <button type="button" class="flex-shrink-0 rounded-md p-1 opacity-60 hover:bg-green-200/60 hover:opacity-100 dark:hover:bg-green-800/50" aria-label="Dismiss" title="Dismiss" @click="dismissed = true">
        <FeatherIcon name="x" class="h-4 w-4" />
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import { online, justReconnected } from '@/data/connection'
import { pendingCount } from '@/data/offlineQueue'

const route = useRoute()

// Closed by the user; it comes back the next time the connection changes.
const dismissed = ref(false)
watch(online, () => (dismissed.value = false))
</script>

<style scoped>
.conn-enter-active,
.conn-leave-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), max-height 0.3s ease;
  max-height: 6rem;
}
.conn-enter-from,
.conn-leave-to {
  opacity: 0;
  transform: translateY(-10px);
  max-height: 0;
  margin-bottom: 0;
}
.conn-pulse-off::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  animation: conn-ping 2s ease-out infinite;
}
.conn-pop {
  animation: conn-pop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes conn-ping {
  from { transform: scale(1); opacity: 0.8; }
  to { transform: scale(1.7); opacity: 0; }
}
@keyframes conn-pop {
  from { transform: scale(0.4); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .conn-pulse-off::after, .conn-pop { animation: none; }
  .conn-enter-active, .conn-leave-active { transition: none; }
}
</style>
