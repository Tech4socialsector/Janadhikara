<template>
  <div class="flex h-12 flex-shrink-0 items-center gap-4 border-b bg-white px-4 dark:border-gray-800 dark:bg-gray-900">
    <div class="flex min-w-0 flex-1 items-center gap-2">
      <Tooltip text="Home">
        <router-link
          :to="{ name: 'Home' }"
          class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          <FeatherIcon name="home" class="h-4 w-4" />
        </router-link>
      </Tooltip>
      <Breadcrumbs />
    </div>

    <div class="flex flex-shrink-0 items-center gap-1">
      <AwesomeBar />
      <TabButtons v-model="theme" :buttons="themeButtons" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FeatherIcon, TabButtons, Tooltip } from 'frappe-ui'
import AwesomeBar from '@/components/AwesomeBar.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { currentTheme } from '@/data/theme'

// Icon-only (hideLabel) so the pair stays compact in a 48px-tall navbar -
// same two values/icons as SettingsDialog's Appearance tab, just a
// different (icon vs text) presentation of the same underlying toggle.
const themeButtons = [
  { label: 'Light', value: 'light', icon: 'sun', hideLabel: true, tooltip: 'Light theme' },
  { label: 'Dark', value: 'dark', icon: 'moon', hideLabel: true, tooltip: 'Dark theme' },
]

const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})
</script>
