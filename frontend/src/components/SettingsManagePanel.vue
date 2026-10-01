<template>
  <div>
    <div class="flex items-start gap-3 rounded-xl border p-4 dark:border-gray-800">
      <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
        <LucideIcon :name="entry.icon" class="h-5 w-5 text-gray-600 dark:text-gray-300" />
      </span>
      <div class="min-w-0 flex-1">
        <div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ entry.label }}</div>
        <p class="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{{ entry.description }}</p>
        <p v-if="entry.count !== null" class="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {{ entry.count }} {{ entry.count === 1 ? 'record' : 'records' }}
        </p>
      </div>
    </div>
    <div class="mt-4 flex flex-wrap gap-2">
      <Button variant="solid" @click="go('DoctypeList')">View {{ entry.label }}</Button>
      <Button v-if="entry.can_create" @click="go('DoctypeNew')">New</Button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import LucideIcon from '@/components/LucideIcon.vue'

const props = defineProps({
  entry: { type: Object, required: true },
})
const emit = defineEmits(['close'])
const router = useRouter()

// Opens the in-app list/new-record page (see router.js, which resolves
// settings doctypes that aren't in any module) and closes the dialog.
function go(name) {
  router.push({ name, params: { doctypeRoute: props.entry.desk_route } })
  emit('close')
}
</script>
