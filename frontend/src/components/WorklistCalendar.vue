<template>
  <div>
    <!-- Header: prev / label / next, the Day | Week | Month switch, and Today. -->
    <div class="mb-3 flex flex-wrap items-center gap-1">
      <Button variant="ghost" size="sm" icon="chevron-left" :tooltip="`Previous ${mode}`" :aria-label="`Previous ${mode}`" @click="shift(-1)" />
      <span class="min-w-0 flex-1 truncate text-center text-sm font-semibold text-ink-gray-9 sm:text-base">{{ rangeLabel }}</span>
      <Button variant="ghost" size="sm" icon="chevron-right" :tooltip="`Next ${mode}`" :aria-label="`Next ${mode}`" @click="shift(1)" />
      <Button size="sm" icon-left="calendar" class="ml-1" @click="goToday">Today</Button>
      <div class="order-last mt-2 flex w-full rounded-lg bg-surface-gray-3 p-0.5 text-sm sm:order-none sm:mt-0 sm:ml-2 sm:w-auto">
        <button
          v-for="m in modes"
          :key="m.value"
          type="button"
          class="flex-1 rounded-md px-3 py-1 sm:flex-none"
          :class="mode === m.value ? 'bg-surface-white font-medium text-ink-gray-9 shadow-sm' : 'text-ink-gray-6 hover:text-ink-gray-8'"
          @click="setMode(m.value)"
        >
          {{ m.label }}
        </button>
      </div>
    </div>

    <div v-if="mode !== 'day'" class="grid grid-cols-7 gap-px overflow-hidden rounded-lg border border-outline-gray-1 bg-outline-gray-1 text-xs">
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
        class="bg-surface-white p-1 sm:p-1.5"
        :class="[
          mode === 'week' ? 'sm:min-h-[20rem]' : 'sm:min-h-[6.5rem]',
          mode === 'month' && !cell.inMonth ? 'bg-surface-gray-1' : '',
          selectedKey === cell.key ? 'sm:bg-surface-white max-sm:bg-surface-blue-1' : '',
        ]"
      >
        <!-- Phone: Google-Calendar style - a compact day with dots; tapping a day
        lists that day's tasks underneath. -->
        <button
          type="button"
          class="flex h-11 w-full flex-col items-center justify-start gap-1 sm:hidden"
          @click="selectDay(cell.key)"
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

    <!-- The selected day's agenda: the whole Day view, and under the grid on a phone. -->
    <div :class="mode === 'day' ? '' : 'mt-4 sm:hidden'">
      <div v-if="mode !== 'day'" class="mb-2 flex items-center justify-between">
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

const modes = [
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
]
const MODE_KEY = 'worklist-calendar-mode'
function savedMode() {
  try {
    const m = localStorage.getItem(MODE_KEY)
    return modes.some((x) => x.value === m) ? m : 'month'
  } catch {
    return 'month'
  }
}
const mode = ref(savedMode())
function setMode(value) {
  mode.value = value
  try {
    localStorage.setItem(MODE_KEY, value)
  } catch {
    // Remembering the choice is a convenience only.
  }
}

const today = new Date()
const todayKey = ymd(today)
// The day everything is centred on: the day shown, the week it is in, or the month it is in.
const anchor = ref(new Date(today.getFullYear(), today.getMonth(), today.getDate()))
const selectedKey = computed(() => ymd(anchor.value))
const dateOf = (key) => new Date(`${key}T00:00:00`)

function selectDay(key) {
  anchor.value = dateOf(key)
}
function shift(delta) {
  const a = anchor.value
  if (mode.value === 'day') anchor.value = new Date(a.getFullYear(), a.getMonth(), a.getDate() + delta)
  else if (mode.value === 'week') anchor.value = new Date(a.getFullYear(), a.getMonth(), a.getDate() + delta * 7)
  else {
    // Same day of the next/previous month, kept inside a shorter month.
    const last = new Date(a.getFullYear(), a.getMonth() + delta + 1, 0).getDate()
    anchor.value = new Date(a.getFullYear(), a.getMonth() + delta, Math.min(a.getDate(), last))
  }
}
function goToday() {
  anchor.value = new Date(today.getFullYear(), today.getMonth(), today.getDate())
}

const weekStart = computed(() => {
  const a = anchor.value
  return new Date(a.getFullYear(), a.getMonth(), a.getDate() - a.getDay())
})

const rangeLabel = computed(() => {
  const a = anchor.value
  if (mode.value === 'day') {
    return a.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  }
  if (mode.value === 'week') {
    const start = weekStart.value
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 6)
    const short = { day: 'numeric', month: 'short' }
    return `${start.toLocaleDateString(undefined, short)} – ${end.toLocaleDateString(undefined, { ...short, year: 'numeric' })}`
  }
  return a.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
})

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

// Month: six weeks around the month. Week: just the seven days of the week.
const calendarCells = computed(() => {
  const month = anchor.value.getMonth()
  const year = anchor.value.getFullYear()
  const gridStart = mode.value === 'week' ? weekStart.value : new Date(year, month, 1 - new Date(year, month, 1).getDay())
  const count = mode.value === 'week' ? 7 : 42
  const cells = []
  for (let i = 0; i < count; i++) {
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
