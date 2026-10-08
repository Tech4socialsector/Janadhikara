<template>
  <div class="fixed inset-0 flex flex-col bg-gray-50 pt-[env(safe-area-inset-top)] dark:bg-gray-900">
    <div class="flex flex-shrink-0 items-center gap-2 border-b bg-white px-3 py-3 dark:border-gray-800 dark:bg-gray-900">
      <!-- Back on every page except Home (where there is nowhere to go back to). -->
      <Button v-if="canGoBack" variant="ghost" size="sm" icon="arrow-left" aria-label="Back" class="-ml-1 flex-shrink-0" @click="goBack" />
      <Button variant="ghost" size="sm" icon="menu" aria-label="Menu" class="flex-shrink-0" :class="canGoBack ? '' : '-ml-1'" @click="openMobileMenu" />
      <!-- The app icon goes Home. -->
      <router-link v-if="!canGoBack" :to="{ name: 'Home' }" class="flex flex-shrink-0 items-center" aria-label="Home">
        <img
          v-if="appLogo"
          :src="appLogo"
          class="h-7 w-7 rounded-lg object-cover"
        />
        <FeatherIcon v-else name="home" class="h-6 w-6 text-gray-500 dark:text-gray-400" />
      </router-link>
      <h1 class="min-w-0 flex-1 truncate text-base font-semibold text-gray-900 dark:text-gray-100">
        {{ pageTitle }}
      </h1>
      <AwesomeBar />
      <LanguageSwitcher />
      <NetworkPill compact />
      <Button
        variant="ghost"
        :icon="theme === 'dark' ? 'moon' : 'sun'"
        :tooltip="theme === 'dark' ? t('Dark theme - switch to light') : t('Light theme - switch to dark')"
        aria-label="Switch theme"
        @click="theme = theme === 'dark' ? 'light' : 'dark'"
      />

      <!-- Alerts in the top-right corner (the profile is in the bottom bar). -->
      <span class="relative inline-flex flex-shrink-0">
        <Button variant="ghost" size="sm" icon="bell" :tooltip="t('Notifications')" aria-label="Notifications" @click="toggleNotifications" />
        <span
          v-if="unreadCount > 0"
          class="pointer-events-none absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-2xs font-medium text-white"
        >
          {{ unreadCount > 9 ? '9+' : unreadCount }}
        </span>
      </span>
    </div>

    <main class="flex-1 overflow-y-auto px-4 py-4 pb-20">
      <ConnectionBanner />
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
import { useRoute, useRouter } from 'vue-router'
import { Button, FeatherIcon } from 'frappe-ui'
import AwesomeBar from '@/components/AwesomeBar.vue'
import NetworkPill from '@/components/NetworkPill.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { currentTheme } from '@/data/theme'
import { t } from '@/utils/translate'
import MobileNav from '@/components/MobileNav.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import NotificationPanel from '@/components/NotificationPanel.vue'
import AiAssistant from '@/components/AiAssistant.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import { appLogo } from '@/data/branding'
import { openMobileMenu } from '@/data/mobileMenu'
import { pageTitle } from '@/data/pageTitle'
import { showSettingsDialog } from '@/data/settingsDialog'
import { unreadCount, toggleNotifications } from '@/data/notifications'

const route = useRoute()
const router = useRouter()
const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})
const canGoBack = computed(() => route.name !== 'Home')

// One step back through the app's own history; if this page was opened directly
// (a link, a push alert) there is none, so go Home instead of leaving the app.
function goBack() {
  if (window.history.state?.back) router.back()
  else router.push({ name: 'Home' })
}

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
