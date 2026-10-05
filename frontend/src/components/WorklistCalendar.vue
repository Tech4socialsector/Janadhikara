<template>
  <div>
    <!-- Month header: prev / month / next, plus Today. -->
    <div class="mb-3 flex items-center gap-1">
      <Button variant="ghost" size="sm" icon="chevron-left" tooltip="Previous month" aria-label="Previous month" @click="shiftMonth(-1)" />
      <span class="flex-1 text-center text-sm font-semibold text-ink-gray-9 sm:text-base">{{ monthLabel }}</span>
      <Button variant="ghost" size="sm" icon="chevron-right" tooltip="Next month" aria-label="Next month" @click="shiftMonth(1)" />
      <Button size="sm" icon-left="calendar" class="ml-1" @click="goToday">Today</Button>
    </div>

    <div class="grid grid-cols-7 gap-px overflow-hidden rounded-lg border border-outline-gray-1 bg-outline-gray-1 text-xs">
      <div
        v-for="day in weekdayLabels"
        :key="day.full"
        class="bg-surface-gray-1 py-1.5 text-center font-medium text-ink-gray-5"
      >
        <span class="hidden sm:inline">{{ day.full }}</span>
        <span class="sm:hidden">{{ day.short }}</span>
      </div>

      <div
        v-for="cell in calendarCells"
        :key="cell.key"
        class="bg-surface-white p-1 sm:min-h-[6.5rem] sm:p-1.5"
        :class="[
          !cell.inMonth ? 'bg-surface-gray-1' : '',
          selectedKey === cell.key ? 'sm:bg-surface-white max-sm:bg-surface-blue-1' : '',
        ]"
      >
        <!-- Phone: Google-Calendar style - a compact day with dots; tapping a day
        lists that day's tasks underneath. -->
        <button
          type="button"
          class="flex h-11 w-full flex-col items-center justify-start gap-1 sm:hidden"
          @click="selectedKey = cell.key"
        >
          <span
            class="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium"
            :class="[
              cell.isToday ? 'bg-blue-600 text-white' : cell.inMonth ? 'text-ink-gray-8' : 'text-ink-gray-4',
              selectedKey === cell.key && !cell.isToday ? 'ring-2 ring-blue-500' : '',
            ]"
          >
            {{ cell.day }}
          </span>
          <span class="flex h-1.5 items-center gap-0.5">
            <span
              v-for="todo in cell.todos.slice(0, 3)"
              :key="todo.name"
              class="h-1.5 w-1.5 rounded-full"
              :class="taskColor(todo, todayKey)"
            />
          </span>
        </button>

        <!-- Desktop: the day number and one chip per task (hover for details). -->
        <div class="hidden sm:block">
          <span
            class="mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium"
            :class="cell.isToday ? 'bg-blue-600 text-white' : cell.inMonth ? 'text-ink-gray-8' : 'text-ink-gray-4'"
          >
            {{ cell.day }}
          </span>
          <TaskHoverCard v-for="todo in cell.todos" :key="todo.name" :todo="todo" class="mb-1 block w-full">
            <button
              type="button"
              class="flex w-full items-center gap-1.5 truncate rounded px-1.5 py-0.5 text-left text-2xs transition-colors"
              :class="chipClass(todo)"
              @click="$emit('open', todo)"
            >
              <span class="h-1.5 w-1.5 flex-shrink-0 rounded-full" :class="taskColor(todo, todayKey)" />
              <span class="truncate"><span v-if="todo.task_time" class="font-medium">{{ formatTime(todo.task_time) }} </span>{{ taskTitle(todo) }}</span>
            </button>
          </TaskHoverCard>
        </div>
      </div>
    </div>

    <!-- Phone: the selected day's agenda. -->
    <div class="mt-4 sm:hidden">
      <div class="mb-2 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-ink-gray-9">{{ selectedLabel }}</h3>
        <span class="text-xs text-ink-gray-5">{{ agenda.length }} {{ agenda.length === 1 ? 'task' : 'tasks' }}</span>
      </div>
      <ul v-if="agenda.length" class="space-y-2">
        <li v-for="todo in agenda" :key="todo.name">
          <button
            type="button"
            class="flex w-full items-stretch gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-3 text-left active:bg-surface-gray-1"
            @click="$emit('open', todo)"
          >
            <span class="w-1 flex-shrink-0 rounded-full" :class="taskColor(todo, todayKey)" />
            <span class="min-w-0 flex-1">
              <span class="block text-sm font-medium text-ink-gray-9" >
                {{ taskTitle(todo) }}
              </span>
              <span v-if="taskDetails(todo)" class="mt-0.5 line-clamp-1 block text-xs text-ink-gray-5">{{ taskDetails(todo) }}</span>
              <span class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-gray-5">
                <span v-if="todo.task_time" class="inline-flex items-center gap-1 font-medium text-ink-gray-7">
                  <FeatherIcon name="clock" class="h-3 w-3" />{{ formatTime(todo.task_time) }}
                </span>
                <span v-if="todo.priority && todo.priority !== 'Medium'" class="inline-flex items-center gap-1 font-medium" :class="todo.priority === 'High' ? 'text-ink-red-4' : ''">
                  <FeatherIcon name="flag" class="h-3 w-3" />{{ todo.priority }}
                </span>
                <span v-if="todo.reference_name" class="inline-flex items-center gap-1">
                  <FeatherIcon name="link" class="h-3 w-3" />{{ todo.reference_type }} · {{ linkTitle(todo.reference_type, todo.reference_name) }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <FeatherIcon name="user" class="h-3 w-3" />{{ userLabel(todo.allocated_to) }}
                </span>
              </span>
            </span>
            <FeatherIcon name="chevron-right" class="h-4 w-4 flex-shrink-0 self-center text-ink-gray-4" />
          </button>
        </li>
      </ul>
      <div v-else class="rounded-xl border border-dashed border-outline-gray-2 py-8 text-center text-sm text-ink-gray-5">
        <FeatherIcon name="calendar" class="mx-auto mb-2 h-5 w-5" />
        Nothing planned for this day.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { FeatherIcon, Button } from 'frappe-ui'
import TaskHoverCard from '@/components/TaskHoverCard.vue'
import { linkTitle } from '@/data/linkTitles'
import { ymd, taskTitle, taskDetails, isOpen, userLabel, taskColor, formatTime } from '@/utils/worklist'

const props = defineProps({
  todos: { type: Array, default: () => [] },
})
defineEmits(['open'])

const weekdayLabels = [
  { full: 'Sun', short: 'S' },
  { full: 'Mon', short: 'M' },
  { full: 'Tue', short: 'T' },
  { full: 'Wed', short: 'W' },
  { full: 'Thu', short: 'T' },
  { full: 'Fri', short: 'F' },
  { full: 'Sat', short: 'S' },
]

const today = new Date()
const todayKey = ymd(today)
const cursor = ref(new Date(today.getFullYear(), today.getMonth(), 1))
const selectedKey = ref(todayKey)

function shiftMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}
function goToday() {
  cursor.value = new Date(today.getFullYear(), today.getMonth(), 1)
  selectedKey.value = todayKey
}

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
)

const todosByDate = computed(() => {
  const map = {}
  for (const todo of props.todos) {
    if (!todo.date) continue
    const key = todo.date.slice(0, 10)
    ;(map[key] ||= []).push(todo)
  }
  for (const key of Object.keys(map)) map[key].sort((a, b) => String(a.task_time || '99').localeCompare(String(b.task_time || '99')))
  return map
})

const calendarCells = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const gridStart = new Date(year, month, 1 - new Date(year, month, 1).getDay())
  const cells = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i)
    const key = ymd(d)
    cells.push({
      key,
      day: d.getDate(),
      inMonth: d.getMonth() === month,
      isToday: key === todayKey,
      todos: todosByDate.value[key] || [],
    })
  }
  return cells
})

const agenda = computed(() => todosByDate.value[selectedKey.value] || [])
const selectedLabel = computed(() =>
  new Date(`${selectedKey.value}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }),
)

function chipClass(todo) {
  if (!isOpen(todo)) return 'bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'
  if (todo.date < todayKey) return 'bg-surface-red-2 text-ink-red-4 hover:bg-surface-red-3'
  return 'bg-surface-blue-2 text-ink-blue-3 hover:bg-surface-blue-3'
}
</script>
