<template>
  <!-- Open tasks assigned to me on this very record (from the Worklist or raised by the
  app, e.g. "Revise household"): shown above the form with a button to close each. -->
  <div v-if="tasks.length" class="mb-4 space-y-2">
    <div
      v-for="task in tasks"
      :key="task.name"
      class="flex items-center gap-3 rounded-xl border border-outline-amber-1 bg-surface-amber-1 px-3 py-2.5"
    >
      <span class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-surface-amber-2 text-ink-amber-3">
        <FeatherIcon name="check-square" class="h-4 w-4" />
      </span>
      <!-- Hover (or tap, on a phone) the task for its full details. -->
      <TaskHoverCard :todo="task" :trigger="isMobile ? 'click' : 'hover'" class="min-w-0 flex-1">
      <div class="min-w-0 cursor-default">
        <p class="truncate text-sm font-medium text-ink-gray-9">{{ taskTitle(task) }}</p>
        <p class="flex flex-wrap items-center gap-x-2 text-xs text-ink-gray-6">
          <span>Task for you</span>
          <span v-if="dueInfo(task)" class="font-medium" :class="dueInfo(task).cls">{{ dueInfo(task).full }}</span>
          <span v-if="task.assigned_by && task.assigned_by !== task.allocated_to">
            · from {{ task.assigned_by_full_name || userLabel(task.assigned_by) }}
          </span>
        </p>
      </div>
      </TaskHoverCard>
      <Button
        size="sm"
        variant="outline"
        icon-left="external-link"
        tooltip="Open this task"
        @click="openInWorklist(task)"
      >
        <span class="max-sm:hidden">Open</span>
      </Button>
      <Button
        size="sm"
        variant="solid"
        theme="green"
        icon-left="lucide-circle-check-big"
        :loading="closing === task.name"
        @click="closeTask(task)"
      >
        <span class="max-sm:hidden">Close task</span>
        <span class="sm:hidden">Close</span>
      </Button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import TaskHoverCard from '@/components/TaskHoverCard.vue'
import { call, toast, FeatherIcon, Button } from 'frappe-ui'
import { session } from '@/data/session'
import { ensureTitlesForRows } from '@/data/linkTitles'
import { taskTitle, dueInfo, userLabel } from '@/utils/worklist'

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
})
const emit = defineEmits(['closed'])

const isMobile = useBreakpoints(breakpointsTailwind).smaller('sm')
const router = useRouter()
const tasks = ref([])
const openInWorklist = (task) => router.push({ name: 'DoctypeForm', params: { doctypeRoute: 'todo', name: task.name } })
const closing = ref(null)

async function load() {
  try {
    const res = await call('frappe.client.get_list', {
      doctype: 'ToDo',
      fields: [
        'name', 'task_title', 'description', 'date', 'task_time', 'status', 'priority', 'creation', 'reference_type',
        'reference_name', 'allocated_to', 'assigned_by', 'assigned_by_full_name',
      ],
      filters: {
        reference_type: props.doctype,
        reference_name: props.name,
        allocated_to: session.user,
        status: 'Open',
      },
      order_by: 'date asc',
      limit_page_length: 20,
    })
    tasks.value = res?.message ?? res ?? []
    // Warm the linked-record titles so the hover card has them the moment it opens.
    const refs = tasks.value.filter((t) => t.reference_type && t.reference_name)
    for (const t of refs) ensureTitlesForRows([{ ref: t.reference_name }], [{ fieldname: 'ref', fieldtype: 'Link', options: t.reference_type }])
  } catch {
    tasks.value = []
  }
}

async function closeTask(task) {
  closing.value = task.name
  try {
    await call('frappe.client.set_value', { doctype: 'ToDo', name: task.name, fieldname: 'status', value: 'Closed' })
    toast.success('Task closed')
    tasks.value = tasks.value.filter((t) => t.name !== task.name)
    emit('closed', task)
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || 'Could not close the task')
  } finally {
    closing.value = null
  }
}

watch(() => [props.doctype, props.name], load, { immediate: true })
</script>
