<template>
  <!-- Header bar: breadcrumbs on the left, search and the theme toggle on the
  right. Page action buttons (Save, New, Delete ...) live in the page's own
  header row (PageHeader), not up here. -->
  <div class="flex h-[3.25rem] flex-shrink-0 items-center gap-4 border-b border-outline-gray-1 bg-surface-white px-5">
    <div class="flex min-w-0 flex-1 items-center gap-2">
      <!-- Back to Home from any other page. -->
      <Button v-if="route.name !== 'Home'" variant="ghost" icon="home" tooltip="Home" aria-label="Go to Home" @click="router.push({ name: 'Home' })" />
      <Breadcrumbs />
    </div>

    <div class="flex flex-shrink-0 items-center gap-2">
      <NetworkPill />
      <AwesomeBar />
      <Button
        variant="ghost"
        :icon="theme === 'dark' ? 'moon' : 'sun'"
        :tooltip="theme === 'dark' ? 'Dark theme - switch to light' : 'Light theme - switch to dark'"
        aria-label="Switch theme"
        @click="theme = theme === 'dark' ? 'light' : 'dark'"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import AwesomeBar from '@/components/AwesomeBar.vue'
import NetworkPill from '@/components/NetworkPill.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { currentTheme } from '@/data/theme'

const route = useRoute()
const router = useRouter()

const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})
</script>
