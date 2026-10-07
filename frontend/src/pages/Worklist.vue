<template>
  <AppLayout>
    <PageHeader class="max-sm:hidden">
      <template #title>
        <!-- A partner admin / supervisor / programme role picks whose worklist to open
        (their own or a team member's) right in the heading; everyone else just
        sees the title. -->
        <FormControl
          v-if="members.length"
          type="select"
          v-model="viewUser"
          :options="viewerOptions"
          class="w-full min-w-[14rem] sm:w-72"
        >
          <template #prefix><FeatherIcon name="users" class="h-4 w-4 text-ink-gray-5" /></template>
        </FormControl>
        <h1 v-else class="text-lg font-semibold text-ink-gray-9 max-sm:hidden sm:text-xl">{{ heading }}</h1>
        <p v-if="viewingOther" class="mt-1 flex items-center gap-1 text-xs text-ink-gray-5">
          <FeatherIcon name="eye" class="h-3 w-3" /> View only
        </p>
      </template>
      <template #actions>
        <TabButtons v-model="view" :buttons="viewButtons" />
        <Button class="max-sm:hidden" variant="solid" size="sm" icon-left="plus" @click="openNew">New task</Button>
      </template>
    </PageHeader>

    <!-- Phone: one compact toolbar (whose list, search, list/calendar) instead of a tall header. -->
    <div class="mb-2 space-y-2 sm:hidden">
      <div class="flex items-center gap-2">
        <FormControl v-if="members.length" type="select" size="md" v-model="viewUser" :options="viewerOptions" class="w-0 min-w-0 flex-1 [&_[data-slot=trigger]]:w-full [&_[data-slot=trigger]_span]:truncate">
          <template #prefix><FeatherIcon name="users" class="h-4 w-4 text-ink-gray-5" /></template>
        </FormControl>
        <h1 v-else class="min-w-0 flex-1 truncate text-base font-semibold text-ink-gray-9">{{ heading }}</h1>
        <Button variant="solid" size="md" icon-left="plus" class="flex-shrink-0" @click="openNew">Add</Button>
      </div>
      <p v-if="viewingOther" class="flex items-center gap-1 text-xs text-ink-gray-5">
        <FeatherIcon name="eye" class="h-3 w-3" /> View only
      </p>
      <div class="flex items-center gap-2">
        <TextInput v-model="search" type="text" size="md" placeholder="Search tasks" class="min-w-0 flex-1">
          <template #prefix><FeatherIcon name="search" class="h-4 w-4 text-ink-gray-5" /></template>
        </TextInput>
        <TabButtons v-model="view" :buttons="viewButtons" class="worklist-view-toggle flex-shrink-0" />
      </div>
    </div>

    <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div class="quick-filters max-w-full sm:overflow-x-auto">
        <TabButtons v-model="filter" :buttons="filterButtons" class="worklist-filter-tabs" />
      </div>
      <TextInput v-model="search" type="text" placeholder="Search tasks" class="w-full max-sm:hidden sm:w-64">
        <template #prefix><FeatherIcon name="search" class="h-4 w-4 text-ink-gray-5" /></template>
      </TextInput>
    </div>

    <div v-if="loading && !all.length" class="space-y-2">
      <Skeleton v-for="i in 4" :key="i" height="4.5rem" />
    </div>
    <ErrorMessage v-else-if="loadError" :message="loadError" />

    <WorklistCalendar v-else-if="view === 'calendar'" :todos="rows" @open="openTask" />

    <template v-else>
      <div
        v-if="rows.length === 0"
        class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-outline-gray-2 py-16 text-center"
      >
        <span class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-gray-2">
          <DoneIcon class="h-5 w-5 text-ink-gray-5" />
        </span>
        <p class="text-sm font-medium text-ink-gray-7">{{ emptyTitle }}</p>
        <p class="max-w-xs text-sm text-ink-gray-5">{{ emptyHint }}</p>
        <Button v-if="!viewingOther" size="sm" icon-left="plus" @click="openNew">New task</Button>
      </div>

      <!-- Grouped by priority: High, Medium, Low, then what's finished. -->
      <div v-else class="space-y-4 pb-24 sm:grid sm:grid-cols-3 sm:items-start sm:gap-4 sm:space-y-0 sm:pb-4">
        <section
          v-for="group in groups"
          :key="group.key"
          :class="group.key === 'done' ? 'sm:col-span-3' : ''"
        >
          <!-- Phone: tap a heading to fold the whole group away (or open it again). -->
          <h2 class="mb-1.5 text-xs font-semibold uppercase tracking-wide" :class="group.titleCls">
            <button
              type="button"
              class="flex w-full items-center gap-1.5 px-0.5 py-1 text-left max-sm:active:opacity-70 sm:px-1 sm:pointer-events-none"
              :aria-expanded="!collapsedGroups.has(group.key)"
              @click="toggleGroup(group.key)"
            >
              <component :is="group.icon" v-if="typeof group.icon !== 'string'" class="h-4 w-4" />
              <FeatherIcon v-else :name="group.icon" class="h-4 w-4" />
              {{ group.label }}
              <span class="rounded-full bg-surface-gray-2 px-1.5 py-0.5 text-2xs font-medium text-ink-gray-6">{{ group.rows.length }}</span>
              <FeatherIcon
                name="chevron-down"
                class="ml-auto h-4 w-4 transition-transform duration-200 sm:hidden"
                :class="collapsedGroups.has(group.key) ? '-rotate-90' : ''"
              />
            </button>
          </h2>

          <ul
            v-show="!isMobile || !collapsedGroups.has(group.key)"
            :class="group.key === 'done' ? 'space-y-2.5 sm:grid sm:grid-cols-3 sm:gap-3 sm:space-y-0' : 'space-y-2.5'"
          >
            <li
              v-if="!group.rows.length"
              class="rounded-lg border border-dashed border-outline-gray-2 py-6 text-center text-sm text-ink-gray-4"
            >
              No tasks
            </li>
            <li
              v-for="row in group.rows"
              :key="row.name"
              class="flex h-[7rem] cursor-pointer items-center gap-3 overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-white py-3 pl-0 pr-3 shadow-sm active:bg-surface-gray-1 sm:hover:bg-surface-gray-1"
              @click="openTask(row)"
            >
              <span class="my-[-0.75rem] w-1 flex-shrink-0 self-stretch" :class="group.bar" />
              <TaskHoverCard :todo="row" class="min-w-0 flex-1">
                <div class="min-w-0">
                  <p
                    class="truncate text-[15px] font-medium leading-snug text-ink-gray-9"
                    :class="row.status !== 'Open' ? 'text-ink-gray-7' : ''"
                  >
                    {{ taskTitle(row) }}
                  </p>
                  <!-- Always one line (blank when there are no details), so every card is the same height. -->
                  <p class="mt-0.5 h-5 truncate text-sm text-ink-gray-5">{{ taskDetails(row) || '\u00a0' }}</p>
                  <div class="mt-2 flex flex-nowrap items-center gap-x-2 overflow-hidden border-t border-outline-gray-1 pt-2 text-xs">
                    <!-- One pill for when it's due: day and time together, coloured by urgency. -->
                    <span v-if="due(row)" class="inline-flex flex-shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 font-medium" :class="duePill(row)">
                      <FeatherIcon :name="row.task_time ? 'clock' : 'calendar'" class="h-3 w-3" />
                      {{ due(row).text }}<template v-if="due(row).time"> · {{ due(row).time }}</template>
                    </span>
                    <span v-if="row.reference_name" class="inline-flex min-w-0 items-center gap-1 text-ink-gray-5">
                      <FeatherIcon name="link" class="h-3 w-3 flex-shrink-0" />
                      <span class="truncate">{{ row.reference_type }} · {{ referenceTitle(row) }}</span>
                    </span>
                    <span v-if="row.assigned_by && row.assigned_by !== row.allocated_to" class="inline-flex items-center gap-1 text-ink-gray-5">
                      <FeatherIcon name="user" class="h-3 w-3" />{{ row.assigned_by_full_name || userLabel(row.assigned_by) }}
                    </span>
                  </div>
                </div>
              </TaskHoverCard>

              <div class="flex flex-shrink-0 items-center gap-1">
                <Button
                  v-if="!viewingOther"
                  size="sm"
                  :variant="row.status === 'Open' ? 'subtle' : 'ghost'"
                  :theme="row.status === 'Open' ? 'green' : 'gray'"
                  :icon-left="'lucide-circle-check-big'"
                  :tooltip="row.status === 'Open' ? 'Mark this task as done' : 'Reopen this task'"
                  :aria-label="row.status === 'Open' ? 'Mark done' : 'Reopen'"
                  :class="[
                    'max-sm:!h-10 max-sm:!w-10 max-sm:!rounded-full max-sm:!border-0 max-sm:!bg-transparent max-sm:!px-0 max-sm:[&_svg]:!h-8 max-sm:[&_svg]:!w-8',
                    row.status === 'Open'
                      ? 'max-sm:!text-gray-400 max-sm:active:!bg-green-100 max-sm:active:!text-green-600'
                      : 'max-sm:!text-green-500',
                  ]"
                  @click.stop="toggleDone(row)"
                >
                  <span class="max-sm:hidden">{{ row.status === 'Open' ? 'Done' : 'Reopen' }}</span>
                </Button>
                <Button
                  v-if="canOpenRecord(row)"
                  class="max-sm:hidden"
                  variant="ghost"
                  size="sm"
                  icon="arrow-up-right"
                  tooltip="Open the record"
                  @click.stop="openRecord(row)"
                />
              </div>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <!-- New task / task details: one popup, small buttons at the end. -->
    <Dialog v-model="showEditor" :options="{ title: editing ? (viewingOther ? 'Task' : 'Edit task') : 'New task', size: 'lg' }">
      <template #body-content>
        <div class="flex flex-col gap-4">
          <FormControl type="text" label="Task title" placeholder="e.g. Visit the Sunrise settlement" v-model="form.title" :disabled="readOnly" />
          <FormControl type="textarea" label="Description" placeholder="Details (optional)" v-model="form.description" :rows="3" :disabled="readOnly" />
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label class="mb-1.5 block text-xs text-ink-gray-5">Due date</label>
              <DatePicker format="DD MMM YYYY" v-model="form.date" :disabled="readOnly" />
            </div>
            <div>
              <label class="mb-1.5 block text-xs text-ink-gray-5">Due time</label>
              <TimePicker v-model="form.time" class="w-full" :disabled="readOnly" />
            </div>
            <FormControl type="select" label="Priority" v-model="form.priority" :options="priorityOptions" :disabled="readOnly" />
          </div>
          <FormControl v-if="editing" type="select" label="Status" v-model="form.status" :options="statusOptions" :disabled="readOnly" />
          <LinkField
            v-if="!editing"
            :field="{ fieldname: 'allocated_to', label: 'Assign to', options: 'User' }"
            v-model="form.allocated_to"
          />
          <p v-else class="text-sm text-ink-gray-5">
            Assigned to <span class="font-medium text-ink-gray-8">{{ userLabel(editing.allocated_to) }}</span>
            <template v-if="editing.assigned_by"> by {{ editing.assigned_by_full_name || userLabel(editing.assigned_by) }}</template>
            <template v-if="editing.creation"> · created {{ createdText(editing) }}</template>
          </p>
          <div v-if="editing && canOpenRecord(editing)">
            <Button size="sm" icon-left="arrow-up-right" @click="openRecord(editing)">
              Open {{ editing.reference_type }} {{ referenceTitle(editing) }}
            </Button>
          </div>
          <ErrorMessage :message="formError" />
        </div>
        <div class="mt-5 flex items-center justify-between gap-2">
          <Button v-if="editing && !readOnly" size="sm" theme="red" variant="subtle" icon-left="trash-2" @click="removeTask">Delete</Button>
          <span v-else />
          <div class="flex gap-2">
            <Button size="sm" icon-left="x" @click="showEditor = false">Close</Button>
            <Button v-if="!readOnly" size="sm" variant="solid" icon-left="check" :loading="saving" @click="saveTask">
              {{ editing ? 'Save' : 'Create' }}
            </Button>
          </div>
        </div>
      </template>
    </Dialog>
  </AppLayout>
</template>

<script setup>
import { ref, computed, reactive, watch, onMounted, h, defineComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import { useList, useCall, call, toast, ErrorMessage, TabButtons, Button, Dialog, FormControl, TextInput, TimePicker, FeatherIcon, DatePicker } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import Skeleton from '@/components/Skeleton.vue'
import LinkField from '@/components/LinkField.vue'
import WorklistCalendar from '@/components/WorklistCalendar.vue'
import TaskHoverCard from '@/components/TaskHoverCard.vue'
import DoneIcon from '@/components/DoneIcon.vue'
import { ymd, plain, isOpen, userLabel, dueInfo, taskTitle, taskDetails } from '@/utils/worklist'
import { session } from '@/data/session'
import { findModuleByDoctype } from '@/data/modules'
import { setPageTitle } from '@/data/pageTitle'
import { linkTitle, ensureTitlesForRows } from '@/data/linkTitles'

setPageTitle('My Worklist')

const router = useRouter()
const route = useRoute()
const view = ref('list') // 'list' | 'calendar'
const filter = ref('open')
const search = ref('')

const viewButtons = [
  { label: 'List', value: 'list', icon: 'list', hideLabel: true, tooltip: 'List' },
  { label: 'Calendar', value: 'calendar', icon: 'calendar', hideLabel: true, tooltip: 'Calendar' },
]
const quickFilterDefs = [
  { label: 'Open', value: 'open', icon: 'circle' },
  { label: 'Overdue', value: 'overdue', icon: 'alert-circle' },
  { label: 'Today', value: 'today', icon: 'sun' },
  { label: 'Done', value: 'done', icon: DoneIcon },
  { label: 'All', value: 'all', icon: 'list' },
]
// Quick filters as a TabButtons strip; the count rides in the label.
// On a phone only the selected one keeps its label, so all five fit on screen
// (the others are icon-only with a tooltip).
const isMobile = useBreakpoints(breakpointsTailwind).smaller('sm')
// The count is a small pill after the label, one colour per tab (solid on the selected one);
// on a phone, where inactive tabs are icon-only, it floats on the icon's corner.
const BADGE_TONES = {
  open: { soft: 'bg-blue-100 text-blue-700', solid: 'bg-blue-600 text-white' },
  overdue: { soft: 'bg-red-100 text-red-700', solid: 'bg-red-600 text-white' },
  today: { soft: 'bg-amber-100 text-amber-800', solid: 'bg-amber-500 text-white' },
  done: { soft: 'bg-green-100 text-green-700', solid: 'bg-green-600 text-white' },
  all: { soft: 'bg-gray-200 text-gray-700', solid: 'bg-gray-700 text-white' },
}
function countBadge(count, { key, selected, floating }) {
  if (!count) return undefined
  const tone = BADGE_TONES[key][selected ? 'solid' : 'soft']
  const cls = [
    'inline-flex items-center justify-center rounded-full font-semibold leading-none tabular-nums',
    floating ? 'absolute -right-1.5 -top-1.5 !h-4 !w-auto min-w-4 px-1 text-[10px] ring-2 ring-white' : '!h-[18px] !w-auto min-w-[18px] px-1.5 text-[11px]',
    tone,
  ]
  return defineComponent({ setup: () => () => h('span', { class: cls }, count > 99 ? '99+' : String(count)) })
}
const filterButtons = computed(() =>
  quickFilterDefs.map((f) => {
    const selected = filter.value === f.value
    const hideLabel = isMobile.value && !selected
    return {
      label: f.label,
      value: f.value,
      icon: f.icon,
      hideLabel,
      tooltip: f.label,
      iconRight: countBadge(counts.value[f.value], { key: f.value, selected, floating: hideLabel }),
    }
  }),
)
const priorityOptions = ['Low', 'Medium', 'High'].map((v) => ({ label: v, value: v }))
const statusOptions = ['Open', 'Closed', 'Cancelled'].map((v) => ({ label: v, value: v }))

// --- Whose worklist --------------------------------------------------------
// Everyone sees their own. Partner admins / supervisors (and programme roles)
// also get a drop-down of the people they oversee - read-only.
const viewUser = ref(session.user)
const membersCall = useCall({ url: '/api/v2/method/janadhikara.worklist.get_team_members', method: 'GET' })
const members = computed(() => membersCall.data || [])
const viewerOptions = computed(() => [
  { label: 'My worklist', value: session.user },
  ...members.value.map((m) => ({ label: `${m.full_name} · ${m.role || 'Worker'}`, value: m.user })),
])
const viewingOther = computed(() => viewUser.value !== session.user)
const viewedName = computed(() => members.value.find((m) => m.user === viewUser.value)?.full_name || userLabel(viewUser.value))
const heading = computed(() => (viewingOther.value ? `${viewedName.value}'s Worklist` : 'My Worklist'))
const readOnly = computed(() => viewingOther.value)

const FIELDS = [
  'name', 'task_title', 'description', 'status', 'date', 'task_time', 'creation', 'priority', 'reference_type',
  'reference_name', 'allocated_to', 'assigned_by', 'assigned_by_full_name', 'modified',
]
const mine = useList({
  doctype: 'ToDo',
  fields: FIELDS,
  filters: () => ({ allocated_to: session.user }),
  orderBy: 'modified desc',
  limit: 300,
})
const team = useCall({
  url: '/api/v2/method/janadhikara.worklist.get_team_tasks',
  method: 'GET',
  params: () => ({ user: viewUser.value }),
  immediate: false,
})
watch(viewUser, (user) => {
  if (user !== session.user) team.fetch()
})
function reload() {
  if (viewingOther.value) team.fetch()
  else mine.reload()
}

const all = computed(() => (viewingOther.value ? team.data : mine.data) || [])
const loading = computed(() => (viewingOther.value ? team.loading : mine.loading))
const loadError = computed(() => (viewingOther.value ? team.error : mine.error))

const today = computed(() => ymd(new Date()))
const isOverdue = (t) => isOpen(t) && t.date && t.date < today.value
const isToday = (t) => isOpen(t) && t.date === today.value

const counts = computed(() => ({
  open: all.value.filter(isOpen).length,
  overdue: all.value.filter(isOverdue).length,
  today: all.value.filter(isToday).length,
  done: all.value.filter((t) => !isOpen(t)).length,
  all: all.value.length,
}))

// Soonest due first (date, then time of day); no date last.
const byDue = (a, b) => {
  const da = `${a.date || '9999-12-31'} ${a.task_time || '99:99'}`
  const db = `${b.date || '9999-12-31'} ${b.task_time || '99:99'}`
  return da < db ? -1 : da > db ? 1 : 0
}

const rows = computed(() => {
  const q = search.value.trim().toLowerCase()
  return all.value
    .filter((t) => {
      if (filter.value === 'open' && !isOpen(t)) return false
      if (filter.value === 'overdue' && !isOverdue(t)) return false
      if (filter.value === 'today' && !isToday(t)) return false
      if (filter.value === 'done' && isOpen(t)) return false
      if (!q) return true
      return [t.task_title, plain(t.description), t.reference_type, t.reference_name, t.assigned_by_full_name, t.priority]
        .join(' ')
        .toLowerCase()
        .includes(q)
    })
    .sort(byDue)
})

const GROUPS = [
  { key: 'High', label: 'High priority', icon: 'flag', titleCls: 'text-ink-red-4', bar: 'bg-red-500' },
  { key: 'Medium', label: 'Medium priority', icon: 'flag', titleCls: 'text-ink-amber-3', bar: 'bg-amber-400' },
  { key: 'Low', label: 'Low priority', icon: 'flag', titleCls: 'text-ink-blue-3', bar: 'bg-blue-400' },
]
const DONE_GROUP = { key: 'done', label: 'Completed', icon: DoneIcon, titleCls: 'text-ink-green-3', bar: 'bg-green-500' }

const groups = computed(() => {
  const list = GROUPS.map((g) => ({
    ...g,
    rows: rows.value.filter((t) => isOpen(t) && (t.priority || 'Medium') === g.key),
  }))
  list.push({ ...DONE_GROUP, rows: rows.value.filter((t) => !isOpen(t)) })
  // Phone: only the groups that have tasks. Window: High / Medium / Low stay as three
  // columns even when one is empty (unless only finished tasks are being shown).
  const showColumns = !isMobile.value && filter.value !== 'done'
  return list.filter((g) => g.rows.length || (showColumns && g.key !== 'done'))
})

watch(
  all,
  (list) => {
    // Record titles, one lookup per referenced doctype.
    const byType = {}
    for (const t of list) if (t.reference_type && t.reference_name) (byType[t.reference_type] ||= []).push(t.reference_name)
    for (const [doctype, names] of Object.entries(byType)) {
      ensureTitlesForRows(
        names.map((n) => ({ ref: n })),
        [{ fieldname: 'ref', fieldtype: 'Link', options: doctype }],
      )
    }
  },
  { immediate: true },
)
const referenceTitle = (t) => linkTitle(t.reference_type, t.reference_name)

const emptyTitle = computed(() => {
  if (search.value) return 'No tasks match your search'
  return { open: "You're all caught up", overdue: 'Nothing overdue', today: 'Nothing due today', done: 'No finished tasks yet', all: 'No tasks yet' }[filter.value]
})
const emptyHint = computed(() =>
  viewingOther.value
    ? 'Nothing here for this person.'
    : 'Tasks assigned to you - by people or by the app (for example a household that needs a revision) - show up here.',
)

// Phone only: which priority groups are folded.
const collapsedGroups = reactive(new Set())
const toggleGroup = (key) => {
  if (!isMobile.value) return
  collapsedGroups.has(key) ? collapsedGroups.delete(key) : collapsedGroups.add(key)
}

const due = (t) => dueInfo(t, today.value)
// Pill colours for the due chip: red when overdue, amber today, grey otherwise.
const duePill = (t) => {
  const cls = due(t)?.cls || ''
  if (cls.includes('red')) return 'bg-surface-red-2 text-ink-red-4'
  if (cls.includes('amber')) return 'bg-surface-amber-2 text-ink-amber-3'
  return 'bg-surface-gray-2 text-ink-gray-6'
}
const createdText = (t) =>
  new Date(String(t.creation).replace(' ', 'T')).toLocaleString([], { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })

// --- Opening a task from a link (a notification, an email, a push alert) ---------
// /worklist?task=<name> opens that task's edit popup. It may be one assigned to
// someone else (the notification said they finished it), so fall back to fetching it.
async function openFromLink(name) {
  if (!name) return
  let task = all.value.find((t) => t.name === name)
  if (!task) {
    try {
      const res = await call('frappe.client.get', { doctype: 'ToDo', name })
      task = res?.message ?? res
    } catch {
      toast.error('That task is no longer available.')
    }
  }
  if (task) router.replace({ name: 'DoctypeForm', params: { doctypeRoute: 'todo', name: task.name } })
  else router.replace({ name: 'Worklist', query: {} })
}
watch(
  () => route.query.task,
  (name) => name && !loading.value && openFromLink(name),
)
onMounted(() => {
  if (route.query.task && !loading.value) openFromLink(route.query.task)
})
watch(loading, (isLoading) => {
  if (!isLoading && route.query.task) openFromLink(route.query.task)
})

// --- Opening the linked record -----------------------------------------
const canOpenRecord = (t) => !!(t.reference_type && t.reference_name && findModuleByDoctype(t.reference_type))
function openRecord(t) {
  const mod = findModuleByDoctype(t.reference_type)
  if (!mod) return
  showEditor.value = false
  router.push({ name: 'DoctypeForm', params: { doctypeRoute: mod.route, name: t.reference_name } })
}

// --- Finish / reopen ------------------------------------------------------
async function toggleDone(t) {
  const status = isOpen(t) ? 'Closed' : 'Open'
  try {
    await call('frappe.client.set_value', { doctype: 'ToDo', name: t.name, fieldname: 'status', value: status })
    toast.success(status === 'Closed' ? 'Marked done' : 'Reopened')
    reload()
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || 'Could not update the task')
  }
}

// --- New task / edit ---------------------------------------------------------
const showEditor = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref(null)
const form = reactive({ title: '', description: '', date: '', time: '', priority: 'Medium', status: 'Open', allocated_to: '' })

function openNew() {
  editing.value = null
  Object.assign(form, {
    title: '',
    description: '',
    date: today.value,
    time: '',
    priority: 'Medium',
    status: 'Open',
    allocated_to: viewingOther.value ? viewUser.value : session.user,
  })
  formError.value = null
  showEditor.value = true
}
// Editing a task opens its full form (the same view as any other record); only a
// brand-new task uses the quick popup.
function openTask(t) {
  router.push({ name: 'DoctypeForm', params: { doctypeRoute: 'todo', name: t.name } })
}
function openTaskPopup(t) {
  editing.value = t
  Object.assign(form, {
    title: t.task_title || plain(t.description),
    description: taskDetails(t),
    date: t.date || '',
    time: t.task_time || '',
    priority: t.priority || 'Medium',
    status: t.status,
    allocated_to: t.allocated_to,
  })
  formError.value = null
  showEditor.value = true
}

async function saveTask() {
  if (!form.title.trim()) {
    formError.value = 'Give the task a title first.'
    return
  }
  saving.value = true
  formError.value = null
  try {
    const values = {
      task_title: form.title.trim(),
      description: form.description.trim() || form.title.trim(),
      date: form.date || null,
      task_time: form.date && form.time ? form.time : null,
      priority: form.priority,
    }
    if (editing.value) {
      await call('frappe.client.set_value', {
        doctype: 'ToDo',
        name: editing.value.name,
        fieldname: { ...values, status: form.status },
      })
    } else {
      await call('frappe.client.insert', {
        doc: { doctype: 'ToDo', ...values, allocated_to: form.allocated_to || session.user, assigned_by: session.user },
      })
    }
    toast.success(editing.value ? 'Task updated' : 'Task created')
    showEditor.value = false
    reload()
  } catch (e) {
    formError.value = e
  } finally {
    saving.value = false
  }
}

async function removeTask() {
  if (!editing.value || !window.confirm('Delete this task?')) return
  try {
    await call('frappe.client.delete', { doctype: 'ToDo', name: editing.value.name })
    toast.success('Task deleted')
    showEditor.value = false
    reload()
  } catch (e) {
    formError.value = e
  }
}
</script>
