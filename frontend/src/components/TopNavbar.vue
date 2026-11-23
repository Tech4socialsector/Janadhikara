<template>
  <!-- Header bar: breadcrumbs on the left, search and the theme toggle on the
  right. Page action buttons (Save, New, Delete ...) live in the page's own
  header row (PageHeader), not up here. -->
  <div class="flex h-[3.25rem] flex-shrink-0 items-center gap-4 border-b border-outline-gray-1 bg-surface-white px-5">
    <div class="flex min-w-0 flex-1 items-center gap-2">
      <!-- With no sidebar (every page except a module that has one) the logo and app name, normally at the top of the
      sidebar, ride here instead. The brand is a link to Home. -->
      <router-link v-if="!hasSidebar" :to="{ name: 'Home' }" class="flex min-w-0 flex-shrink-0 items-center gap-2.5 rounded-lg px-2 py-1.5 duration-150 ease-in-out hover:bg-surface-gray-1" :aria-label="t('Home')">
        <img v-if="appLogo" :src="appLogo" class="h-8 max-w-[7.5rem] flex-shrink-0 object-contain object-left" alt="Logo" />
        <span class="truncate text-[0.9375rem] font-bold text-ink-gray-8">{{ appName }}</span>
      </router-link>
      <span v-if="!hasSidebar && route.name !== 'Home'" class="h-6 w-px flex-shrink-0 bg-outline-gray-3" />
      <template v-if="route.name !== 'Home'">
        <Breadcrumbs />
      </template>
    </div>

    <div class="flex flex-shrink-0 items-center gap-2">
      <NetworkPill />
      <AwesomeBar />
      <LanguageSwitcher />
      <Button
        variant="ghost"
        :icon="theme === 'dark' ? 'moon' : 'sun'"
        :tooltip="theme === 'dark' ? t('Dark theme - switch to light') : t('Light theme - switch to dark')"
        aria-label="Switch theme"
        @click="theme = theme === 'dark' ? 'light' : 'dark'"
      />
      <ProfileMenu />
    </div>
    <!-- The Settings dialog normally rides with the sidebar; on a page without one it is here -->
    <SettingsDialog v-if="!hasSidebar" v-model="showSettingsDialog" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import AwesomeBar from '@/components/AwesomeBar.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import NetworkPill from '@/components/NetworkPill.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ProfileMenu from '@/components/ProfileMenu.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import { showSettingsDialog } from '@/data/settingsDialog'
import { currentTheme } from '@/data/theme'
import { activeModule } from '@/data/activeModule'
import { brandingResource, appLogo } from '@/data/branding'
import { t } from '@/utils/translate'

const route = useRoute()
const router = useRouter()

const hasSidebar = computed(() => !!activeModule.value?.sidebar && route.name !== 'Home')
const appName = computed(() => brandingResource.data?.app_name || 'Janadhikara')

const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})
</script>
