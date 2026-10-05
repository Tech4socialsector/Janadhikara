<template>
  <!-- Hover a task (list row or calendar chip) for its details, without opening it. -->
  <!-- On a phone there is no hover (a tap would pop it up by accident), so the card is skipped. -->
  <div v-if="isMobile" :class="$attrs.class"><slot /></div>
  <Popover v-else :trigger="trigger" :hover-delay="0" :leave-delay="0.15" placement="bottom-start" :class="$attrs.class">
    <template #target><slot /></template>
    <template #body-main>
      <div class="w-72 max-w-[85vw] space-y-2.5 p-3">
        <div class="flex items-start gap-2">
          <DoneIcon
            class="mt-0.5 h-4 w-4 flex-shrink-0"
            :class="isOpen(todo) ? 'text-ink-gray-4' : 'text-ink-green-3'"
          />
          <div class="min-w-0">
            <p class="line-clamp-3 text-sm font-semibold text-ink-gray-9" >
              {{ taskTitle(todo) }}
            </p>
            <p v-if="taskDetails(todo)" class="mt-1 line-clamp-4 text-xs text-ink-gray-6">{{ taskDetails(todo) }}</p>
          </div>
        </div>
        <dl class="space-y-1.5 text-xs text-ink-gray-6">
          <div v-if="due" class="flex items-center gap-2">
            <FeatherIcon name="calendar" class="h-3.5 w-3.5 flex-shrink-0" />
            <span class="font-medium" :class="due.cls">{{ due.full }}</span>
          </div>
          <div class="flex items-center gap-2">
            <FeatherIcon name="flag" class="h-3.5 w-3.5 flex-shrink-0" />
            <span class="rounded-full px-2 py-0.5 font-medium" :class="priorityClass(todo.priority)">{{ todo.priority || 'Medium' }}</span>
            <span class="ml-auto rounded-full bg-surface-gray-2 px-2 py-0.5">{{ todo.status }}</span>
          </div>
          <div v-if="todo.reference_name" class="flex items-center gap-2">
            <FeatherIcon name="link" class="h-3.5 w-3.5 flex-shrink-0" />
            <span class="truncate">{{ todo.reference_type }} · {{ linkTitle(todo.reference_type, todo.reference_name) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <FeatherIcon name="user" class="h-3.5 w-3.5 flex-shrink-0" />
            <span class="truncate">
              {{ userLabel(todo.allocated_to) }}<template v-if="todo.assigned_by && todo.assigned_by !== todo.allocated_to"> · from {{ todo.assigned_by_full_name || userLabel(todo.assigned_by) }}</template>
            </span>
          </div>
        </dl>
        <p class="border-t border-outline-gray-1 pt-2 text-xs text-ink-gray-5">
          <template v-if="todo.creation">Created {{ createdText }}. </template>Tap or click the task to open it.
        </p>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { computed } from 'vue'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import { Popover, FeatherIcon } from 'frappe-ui'
import DoneIcon from '@/components/DoneIcon.vue'
import { linkTitle } from '@/data/linkTitles'
import { taskTitle, taskDetails, isOpen, dueInfo, priorityClass, userLabel } from '@/utils/worklist'

defineOptions({ inheritAttrs: false })
const props = defineProps({
  todo: { type: Object, required: true },
  // 'hover' on desktop; 'click' for the info button on a phone (touch has no hover).
  trigger: { type: String, default: 'hover' },
})
const createdText = computed(() =>
  new Date(String(props.todo.creation).replace(' ', 'T')).toLocaleString([], { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }),
)
const isMobile = useBreakpoints(breakpointsTailwind).smaller('sm')
const due = computed(() => dueInfo(props.todo))
</script>
