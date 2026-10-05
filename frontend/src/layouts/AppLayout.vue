<template>
  <!-- fixed inset-0, not h-screen: 100vh can go stale after the browser's viewport
  changes (closing DevTools, leaving responsive mode) and leave the shell
  stopping short of the window with a blank band below it. Pinning to the
  window edges always matches the real size (and on phones ignores the
  collapsing URL bar that 100vh overshoots). -->
  <MobileShell v-if="isMobile">
    <slot />
  </MobileShell>
  <div v-else class="fixed inset-0 flex bg-surface-white text-ink-gray-8">
    <AppSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <TopNavbar />
      <main class="flex-1 overflow-y-auto bg-surface-white px-5 py-4 sm:px-6">
        <ConnectionBanner />
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import AppSidebar from '@/components/AppSidebar.vue'
import TopNavbar from '@/components/TopNavbar.vue'
import MobileShell from '@/components/MobileShell.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import { startRealtime } from '@/data/realtime'
import { startAutoCleanup } from '@/data/offlineCleanup'

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('sm')

// Live notifications (a task assigned to you shows up at once).
startRealtime()
// Back online: upload what was saved offline and clear the device (see data/offlineCleanup.js).
startAutoCleanup()
</script>
