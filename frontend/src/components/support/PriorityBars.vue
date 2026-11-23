<template>
  <!-- Helpdesk's priority glyph: signal bars, filled up to the priority's level -->
  <svg viewBox="0 0 16 16" class="h-4 w-4 flex-shrink-0" role="img" :aria-label="priority">
    <rect v-for="i in 4" :key="i" :x="1 + (i - 1) * 3.8" :y="14 - i * 3" width="2.6" :height="i * 3" rx="0.8" :class="i <= level ? colour : 'fill-gray-300 dark:fill-gray-600'" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ priority: { type: String, default: 'Medium' } })
const level = computed(() => ({ Low: 1, Medium: 2, High: 3, Urgent: 4 })[props.priority] || 2)
const colour = computed(() => (props.priority === 'Urgent' ? 'fill-red-600' : props.priority === 'High' ? 'fill-orange-500' : 'fill-gray-600 dark:fill-gray-300'))
</script>
