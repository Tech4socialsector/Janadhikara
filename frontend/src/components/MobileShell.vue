<template>
  <div class="flex h-screen flex-col bg-gray-50 dark:bg-gray-900">
    <div class="flex flex-shrink-0 items-center gap-3 border-b bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-900">
      <img
        v-if="appLogo"
        :src="appLogo"
        class="h-7 w-7 flex-shrink-0 rounded-lg object-cover"
      />
      <FeatherIcon v-else name="activity" class="h-6 w-6 flex-shrink-0 text-gray-500 dark:text-gray-400" />
      <h1 class="min-w-0 flex-1 truncate text-base font-semibold text-gray-900 dark:text-gray-100">
        {{ pageTitle }}
      </h1>
      <AwesomeBar />
      <TabButtons v-model="theme" :buttons="themeButtons" />
    </div>

    <main class="flex-1 overflow-y-auto px-4 py-4 pb-20">
      <slot />
    </main>

    <MobileNav />
    <NotificationPanel />
    <AiAssistant />
    <SettingsDialog v-model="showSettingsDialog" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FeatherIcon, TabButtons } from 'frappe-ui'
import AwesomeBar from '@/components/AwesomeBar.vue'
import MobileNav from '@/components/MobileNav.vue'
import NotificationPanel from '@/components/NotificationPanel.vue'
import AiAssistant from '@/components/AiAssistant.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import { appLogo } from '@/data/branding'
import { pageTitle } from '@/data/pageTitle'
import { showSettingsDialog } from '@/data/settingsDialog'
import { currentTheme } from '@/data/theme'

const themeButtons = [
  { label: 'Light', value: 'light', icon: 'sun', hideLabel: true, tooltip: 'Light theme' },
  { label: 'Dark', value: 'dark', icon: 'moon', hideLabel: true, tooltip: 'Dark theme' },
]

const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})
</script>

<style>
/* frappe-ui's toast viewport (see ToastProvider.vue) is a fixed,
bottom-0 <ol> with no id/data-attribute of its own to hook - only this
exact literal class list - so it has to be matched by the full
attribute value. It's rendered once at the app root (outside this
component's own subtree), so this can't be a scoped style; it's global
but only takes effect while MobileShell is mounted, i.e. only on
mobile, which is exactly when it needs to clear MobileNav's bar
instead of covering it. Offset matches MobileNav's own box model: ~56px
content (icon + label + vertical py-2*2) plus its own
env(safe-area-inset-bottom) padding. */
.fixed.bottom-0.items-end.right-0.flex.flex-col.p-5[class*='z-[2147483647]'] {
  bottom: calc(56px + env(safe-area-inset-bottom)) !important;
}
</style>
