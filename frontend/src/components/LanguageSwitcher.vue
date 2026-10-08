<template>
  <!-- Language switcher for the top bar. Hidden when only one language is enabled. -->
  <Dropdown v-if="languages.length > 1" :options="options" placement="bottom-end">
    <template #default>
      <Button variant="ghost" icon-left="globe" :tooltip="`Language: ${currentLabel}`" aria-label="Change language">
        <span class="text-sm">{{ shortLabel }}</span>
      </Button>
    </template>
  </Dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { Button, Dropdown } from 'frappe-ui'
import { appLanguage, languages, setUserLanguage } from '@/data/language'

const currentLabel = computed(() => languages.value.find((l) => l.value === appLanguage.value)?.label || appLanguage.value)
const shortLabel = computed(() => appLanguage.value.split('-')[0].toUpperCase())

const options = computed(() =>
  languages.value.map((l) => ({
    label: l.label,
    icon: l.value === appLanguage.value ? 'check' : undefined,
    onClick: () => setUserLanguage(l.value),
  })),
)
</script>
