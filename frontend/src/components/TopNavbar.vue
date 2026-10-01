<template>
  <!-- Header bar: breadcrumbs on the left, search and the theme toggle on the
  right. Page action buttons (Save, New, Delete ...) live in the page's own
  header row (PageHeader), not up here. -->
  <div class="flex h-[3.25rem] flex-shrink-0 items-center gap-4 border-b border-outline-gray-1 bg-surface-white px-5">
    <div class="flex min-w-0 flex-1 items-center">
      <Breadcrumbs />
    </div>

    <div class="flex flex-shrink-0 items-center gap-2">
      <AwesomeBar />
      <TabButtons v-model="theme" :buttons="themeButtons" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { TabButtons } from 'frappe-ui'
import AwesomeBar from '@/components/AwesomeBar.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { currentTheme } from '@/data/theme'

// Icon-only (hideLabel) so the pair stays compact in the header bar - same
// two values/icons as SettingsDialog's Appearance tab, just a different
// (icon vs text) presentation of the same underlying toggle.
const themeButtons = [
  { label: 'Light', value: 'light', icon: 'sun', hideLabel: true, tooltip: 'Light theme' },
  { label: 'Dark', value: 'dark', icon: 'moon', hideLabel: true, tooltip: 'Dark theme' },
]

const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})
</script>
