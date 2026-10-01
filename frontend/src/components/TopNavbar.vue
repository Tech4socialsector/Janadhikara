<template>
  <!-- One header bar, like Frappe Helpdesk's LayoutHeader: breadcrumbs on the
  left; on the right, whatever the current page puts in the actions slot
  (PageHeader teleports its buttons into #page-header-actions - Save, New,
  Delete...), then search and the theme toggle. -->
  <div class="flex h-[3.25rem] flex-shrink-0 items-center gap-4 border-b border-outline-gray-1 bg-surface-white px-5">
    <div class="flex min-w-0 flex-1 items-center">
      <Breadcrumbs />
    </div>

    <div class="flex flex-shrink-0 items-center gap-2">
      <div id="page-header-actions" class="flex items-center gap-2 empty:hidden" />
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
