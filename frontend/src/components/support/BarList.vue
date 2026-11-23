<template>
  <div class="space-y-1.5">
    <div v-for="[label, n] in entries" :key="label" class="flex items-center gap-2 text-sm">
      <span class="w-36 flex-shrink-0 truncate text-gray-600 dark:text-gray-300">{{ t(label) }}</span>
      <div class="h-2 flex-1 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
        <div class="h-full rounded-full bg-gray-700 dark:bg-gray-300" :style="{ width: `${(n / max) * 100}%` }" />
      </div>
      <span class="w-8 text-right tabular-nums text-gray-900 dark:text-gray-100">{{ n }}</span>
    </div>
    <p v-if="!entries.length" class="text-sm text-gray-400">{{ t('Nothing open.') }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t } from '@/utils/translate'

const props = defineProps({ data: { type: Object, default: () => ({}) }, order: { type: Array, default: () => [] } })
const entries = computed(() => {
  const known = props.order.filter((k) => props.data[k]).map((k) => [k, props.data[k]])
  const rest = Object.entries(props.data).filter(([k]) => !props.order.includes(k))
  return [...known, ...rest]
})
const max = computed(() => Math.max(1, ...entries.value.map(([, n]) => n)))
</script>
