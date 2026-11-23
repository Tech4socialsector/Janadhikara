<template>
  <AppLayout>
    <!-- Slim header, as in Frappe Helpdesk: breadcrumbs (with the saved views as a menu on the queue) and Create -->
    <div class="-mx-4 -mt-4 mb-3 flex min-h-[2.75rem] items-center justify-between gap-2 border-b px-4 py-1.5 dark:border-gray-800 sm:-mx-6 sm:mb-4 sm:px-5">
      <nav class="flex min-w-0 items-center gap-1.5 text-base" :aria-label="t('Breadcrumb')">
        <Dropdown :options="viewMenu">
          <button class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium text-ink-gray-9 hover:bg-surface-gray-2">
            {{ currentViewLabel }}<FeatherIcon name="chevron-down" class="h-3.5 w-3.5 text-ink-gray-5" />
          </button>
        </Dropdown>
        <span v-if="options?.city" class="ml-2 hidden rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-6 sm:inline">{{ options.city }}</span>
      </nav>
      <div class="flex flex-shrink-0 items-center gap-2">
        <template v-if="selected.length && view !== 'overview'">
          <Dropdown :options="actionsMenu" placement="right">
            <Button variant="solid">
              {{ t('Actions') }}
              <template #suffix><FeatherIcon name="chevron-down" class="h-4 w-4" /></template>
            </Button>
          </Dropdown>
        </template>
        <Button variant="solid" :aria-label="t('Create')" @click="router.push({ name: 'SupportNew' })">
          <template #prefix><FeatherIcon name="plus" class="h-4 w-4" /></template>
          {{ t('Create') }}
        </Button>
      </div>
    </div>

    <!-- Overview (manager) -->
    <div v-if="view === 'overview'" class="space-y-6">
      <div v-if="overview" class="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <button v-for="card in cards" :key="card.label" class="rounded-xl border p-4 text-left transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50" @click="openQueue(card)">
          <p class="text-xs text-gray-500 dark:text-gray-400">{{ card.label }}</p>
          <p class="mt-1 text-2xl font-semibold tabular-nums" :class="card.warn && card.value ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'">{{ card.value }}</p>
        </button>
      </div>
      <Skeleton v-else height="5rem" />
      <div v-if="overview" class="grid gap-6 lg:grid-cols-2">
        <section class="rounded-xl border p-4 dark:border-gray-800">
          <h2 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Response times (last 90 days)') }}</h2>
          <dl class="grid grid-cols-2 gap-3 text-sm">
            <div><dt class="text-gray-500">{{ t('Average first response') }}</dt><dd class="text-lg font-semibold">{{ hours(overview.avg_first_response_hours) }}</dd></div>
            <div><dt class="text-gray-500">{{ t('Average resolution') }}</dt><dd class="text-lg font-semibold">{{ hours(overview.avg_resolution_hours) }}</dd></div>
          </dl>
        </section>
        <section class="rounded-xl border p-4 dark:border-gray-800">
          <h2 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Created and resolved, last 14 days') }}</h2>
          <svg viewBox="0 0 280 70" class="h-20 w-full" role="img" :aria-label="t('Tickets created and resolved per day')">
            <g v-for="(d, i) in overview.days" :key="d.date">
              <rect :x="i * 20 + 1" :y="60 - (d.created / dayMax) * 55" width="8" :height="(d.created / dayMax) * 55" rx="1" class="fill-gray-700 dark:fill-gray-300"><title>{{ d.date }}: {{ d.created }} {{ t('created') }}</title></rect>
              <rect :x="i * 20 + 10" :y="60 - (d.resolved / dayMax) * 55" width="8" :height="(d.resolved / dayMax) * 55" rx="1" class="fill-green-500"><title>{{ d.date }}: {{ d.resolved }} {{ t('resolved') }}</title></rect>
            </g>
          </svg>
          <p class="mt-1 text-xs text-gray-500"><span class="mr-3">&#9632; {{ t('Created') }}</span><span class="text-green-600">&#9632; {{ t('Resolved') }}</span></p>
        </section>
        <section class="rounded-xl border p-4 dark:border-gray-800"><h2 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Open by status') }}</h2><BarList :data="overview.by_status" :order="options.statuses" /></section>
        <section class="rounded-xl border p-4 dark:border-gray-800"><h2 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Open by priority') }}</h2><BarList :data="overview.by_priority" :order="[...options.priorities].reverse()" /></section>
        <section class="rounded-xl border p-4 dark:border-gray-800"><h2 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Open by type') }}</h2><BarList :data="overview.by_type" :order="options.types" /></section>
        <section class="rounded-xl border p-4 dark:border-gray-800">
          <h2 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Open tickets per agent') }}</h2>
          <BarList :data="Object.fromEntries(overview.agent_load.map((a) => [a.name, a.open]))" />
        </section>
      </div>
    </div>

    <!-- Tickets: mine, or the queue -->
    <template v-else>
      <!-- View controls: on a computer the quick filters sit in a row; on a phone they fold into a panel behind "Filters" -->
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          <div class="relative min-w-0 flex-1 sm:w-56 sm:flex-none">
            <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-gray-5" />
            <input v-model="search" type="search" :placeholder="t('Subject, ID or requester')" class="h-9 w-full appearance-none rounded border-0 bg-surface-gray-2 pl-8 pr-2 text-base placeholder-ink-gray-4 shadow-none hover:bg-surface-gray-3 focus:bg-surface-white focus:outline-none focus:ring-2 focus:ring-outline-gray-3 sm:h-7" />
          </div>
          <Button class="relative sm:!hidden" :aria-label="t('Filters')" :aria-expanded="showFilters" @click="showFilters = !showFilters">
            <FeatherIcon name="sliders" class="h-4 w-4" />
            <span v-if="activeFilterCount" class="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-ink-gray-9 px-1 text-[10px] font-medium text-white">{{ activeFilterCount }}</span>
          </Button>
          <div class="w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap sm:items-center" :class="showFilters ? 'grid' : 'hidden sm:flex'">
            <FormControl v-model="status" type="select" size="sm" class="sm:w-36 [&_[data-slot=trigger]]:w-full" :options="statusOptions" />
            <FormControl v-model="priority" type="select" size="sm" class="sm:w-32 [&_[data-slot=trigger]]:w-full" :options="priorityOptions" />
            <FormControl v-if="view === 'queue'" v-model="type" type="select" size="sm" class="sm:w-36 [&_[data-slot=trigger]]:w-full" :options="typeOptions" />
            <Button v-if="filtered" class="col-span-2" variant="ghost" size="sm" @click="clearFilters">{{ t('Clear filters') }}</Button>
          </div>
        </div>
        <div class="flex flex-shrink-0 items-center gap-2">
          <Dropdown :options="sortMenu" placement="right">
            <Button variant="subtle" size="sm" :aria-label="t('Sort')">
              <template #prefix><FeatherIcon name="arrow-down" class="h-4 w-4" /></template>
              <span class="hidden sm:inline">{{ sortOptions.find((o) => o.value === sort)?.label }}</span>
              <template #suffix><FeatherIcon name="chevron-down" class="hidden h-4 w-4 sm:block" /></template>
            </Button>
          </Dropdown>
          <Button variant="subtle" size="sm" :tooltip="t('Refresh')" :aria-label="t('Refresh')" @click="load()"><FeatherIcon name="refresh-cw" class="h-4 w-4" /></Button>
        </div>
      </div>

      <Dialog v-model="confirmDelete" :options="{ title: t('Delete tickets'), message: `${t('Delete')} ${selected.length} ${t(selected.length === 1 ? 'ticket' : 'tickets')}? ${t('Their replies are deleted too. This cannot be undone.')}`, size: 'sm', actions: [{ label: t('Delete'), variant: 'solid', theme: 'red', onClick: doDelete }] }" />

      <div v-if="loading" class="space-y-2"><Skeleton v-for="i in 5" :key="i" height="3.25rem" /></div>
      <ErrorMessage v-else-if="error" :message="error" />
      <div v-else-if="!tickets.length" class="rounded-xl border border-dashed py-16 text-center dark:border-gray-800">
        <FeatherIcon name="inbox" class="mx-auto mb-3 h-8 w-8 text-gray-300" />
        <p class="text-sm font-medium text-gray-700 dark:text-gray-200">{{ view === 'mine' && !filtered ? t('You have not raised a ticket yet.') : t('No tickets match.') }}</p>
        <Button v-if="view === 'mine' && !filtered" class="mt-4" variant="solid" icon-left="plus" @click="router.push({ name: 'SupportNew' })">{{ t('Raise your first ticket') }}</Button>
      </div>
      <template v-else>
        <TicketTable v-model:selected="selected" :rows="tickets" :agent="view === 'queue'" />
        <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-base text-ink-gray-5">
          <div class="flex items-center gap-2">
            <span>{{ t('Rows per page') }}</span>
            <FormControl v-model="pageSize" type="select" size="sm" class="w-20 [&_[data-slot=trigger]]:w-full" :options="[25, 50, 100].map((n) => ({ label: String(n), value: n }))" />
          </div>
          <div class="flex items-center gap-3">
            <span>{{ t('Showing') }} {{ tickets.length }} {{ t(tickets.length === 1 ? 'ticket' : 'tickets') }}</span>
            <Button v-if="hasMore" variant="subtle" :loading="loadingMore" @click="loadMore">{{ t('Load more') }}</Button>
          </div>
        </div>
      </template>
    </template>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Button, Dialog, Dropdown, FormControl, ErrorMessage, FeatherIcon, toast } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import Skeleton from '@/components/Skeleton.vue'
import TicketTable from '@/components/support/TicketTable.vue'
import BarList from '@/components/support/BarList.vue'
import { loadSupportOptions, supportOptions, listTickets, updateTicket, deleteTickets, getOverview } from '@/data/support'
import { setPageTitle } from '@/data/pageTitle'
import { t } from '@/utils/translate'

setPageTitle('Support')
const router = useRouter()
const route = useRoute()
const options = supportOptions
const view = ref(route.query.view || 'mine')
const queueView = ref(route.query.q || 'open')
const tickets = ref([])
const hasMore = ref(false)
const overview = ref(null)
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const search = ref('')
const status = ref('')
const priority = ref('')
const type = ref('')
const showFilters = ref(false)
const activeFilterCount = computed(() => [status.value, priority.value, type.value].filter(Boolean).length)
const sort = ref('modified')
const selected = ref([])
const pageSize = ref(25)

const tabs = computed(() => [
  { key: 'mine', label: t('My tickets') },
  ...(options.value?.is_agent ? [{ key: 'queue', label: t('Queue') }] : []),
  ...(options.value?.is_manager ? [{ key: 'overview', label: t('Overview') }] : []),
])
// The queue's saved views: each is a set of filters the lists below add to
const queueViews = computed(() => [
  { key: 'open', label: t('All open') },
  { key: 'me', label: t('Assigned to me') },
  { key: 'unassigned', label: t('Unassigned') },
  { key: 'overdue', label: t('Overdue') },
  { key: 'done', label: t('Resolved and closed') },
  { key: 'all', label: t('Everything') },
])
// One menu of views in the header, as in Helpdesk: my own tickets, the team's saved queue views, and the overview
const viewMenu = computed(() => [
  { group: t('Mine'), items: [{ label: t('My tickets'), icon: 'user', onClick: () => (view.value = 'mine') }] },
  ...(options.value?.is_agent
    ? [{ group: t('Queue'), items: queueViews.value.map((v) => ({ label: v.label, icon: 'inbox', onClick: () => { view.value = 'queue'; queueView.value = v.key } })) }]
    : []),
  ...(options.value?.is_manager ? [{ group: t('Reports'), items: [{ label: t('Overview'), icon: 'bar-chart-2', onClick: () => (view.value = 'overview') }] }] : []),
])
const currentViewLabel = computed(() => (view.value === 'queue' ? queueViews.value.find((v) => v.key === queueView.value)?.label : view.value === 'overview' ? t('Overview') : t('My tickets')))
const viewFilters = () => {
  if (view.value !== 'queue') return {}
  return {
    open: {},
    me: { assigned_to: 'me' },
    unassigned: { assigned_to: 'unassigned' },
    overdue: { overdue: 1 },
    done: { statuses: ['Resolved', 'Closed'] },
    all: { everything: true },
  }[queueView.value]
}
const statusOptions = computed(() => [{ label: t('Any status'), value: '' }, ...(options.value?.statuses || []).map((s) => ({ label: t(s), value: s }))])
const priorityOptions = computed(() => [{ label: t('Any priority'), value: '' }, ...(options.value?.priorities || []).map((s) => ({ label: t(s), value: s }))])
const typeOptions = computed(() => [{ label: t('Any type'), value: '' }, ...(options.value?.types || []).map((s) => ({ label: t(s), value: s }))])
const sortOptions = computed(() => [
  { label: t('Latest activity'), value: 'modified' },
  { label: t('Newest first'), value: 'created' },
  { label: t('Oldest first'), value: 'oldest' },
  { label: t('Respond by (soonest)'), value: 'due' },
  { label: t('Priority (highest)'), value: 'priority' },
])
const sortMenu = computed(() => sortOptions.value.map((o) => ({ label: o.label, icon: sort.value === o.value ? 'check' : undefined, onClick: () => (sort.value = o.value) })))
const filtered = computed(() => !!(search.value || status.value || priority.value || type.value))
const cards = computed(() => {
  const o = overview.value
  return o
    ? [
        { label: t('Open'), value: o.open, view: 'open' },
        { label: t('Unassigned'), value: o.unassigned, view: 'unassigned', warn: true },
        { label: t('Overdue'), value: o.overdue, view: 'overdue', warn: true },
        { label: t('Urgent'), value: o.urgent, view: 'open', priority: 'Urgent', warn: true },
        { label: t('Waiting on requester'), value: o.waiting, view: 'open', status: 'Waiting on Requester' },
      ]
    : []
})
const dayMax = computed(() => Math.max(1, ...(overview.value?.days || []).flatMap((d) => [d.created, d.resolved])))
const hours = (h) => (h == null ? '-' : h < 48 ? `${h} h` : `${(h / 24).toFixed(1)} d`)

function clearFilters() {
  search.value = status.value = priority.value = type.value = ''
}
function openQueue(card) {
  status.value = card.status || ''
  priority.value = card.priority || ''
  queueView.value = card.view
  view.value = 'queue'
}

const clean = (e) => String(e?.messages?.[0] || e?.message || t('The tickets could not be loaded.')).replace(/<[^>]+>/g, '')
function query(start) {
  const f = viewFilters()
  return {
    scope: view.value === 'mine' ? 'mine' : f.everything || f.statuses || status.value ? 'all' : 'queue',
    status: status.value || (f.statuses ? f.statuses.join(',') : undefined),
    priority: priority.value || undefined,
    ticket_type: type.value || undefined,
    assigned_to: f.assigned_to,
    overdue: f.overdue,
    search: search.value || undefined,
    sort: sort.value,
    start,
    page_length: pageSize.value,
  }
}
let seq = 0
async function load() {
  if (view.value === 'overview') {
    try {
      overview.value = await getOverview()
    } catch (e) {
      error.value = clean(e)
    }
    loading.value = false
    return
  }
  const mine = ++seq
  loading.value = !tickets.value.length
  error.value = ''
  selected.value = []
  try {
    const res = await listTickets(query(0))
    if (mine !== seq) return
    tickets.value = res.rows
    hasMore.value = res.has_more
  } catch (e) {
    if (mine === seq) error.value = clean(e)
  }
  loading.value = false
}
async function loadMore() {
  loadingMore.value = true
  try {
    const res = await listTickets(query(tickets.value.length))
    tickets.value = [...tickets.value, ...res.rows]
    hasMore.value = res.has_more
  } catch (e) {
    toast.error(clean(e))
  }
  loadingMore.value = false
}
// Run one change on every ticked ticket, then say how it went
async function forSelected(work, done) {
  const names = [...selected.value]
  const results = await Promise.allSettled(names.map((name) => work(name)))
  const failed = results.filter((r) => r.status === 'rejected').length
  if (failed) toast.error(`${failed} ${t('could not be changed.')}`)
  else toast.success(`${names.length} ${t(done)}`)
  load()
}
const bulk = (changes) => forSelected((name) => updateTicket({ name, ...changes }), 'tickets updated')

// The Actions menu: update, tag, export and (managers) delete
const actionsMenu = computed(() => {
  const o = options.value || {}
  const groups = [
    {
      group: t('Update'),
      items: [
        { label: t('Assign to'), icon: 'user-plus', submenu: [{ label: t('Me'), onClick: () => bulk({ assigned_to: o.user }) }, ...(o.agents || []).filter((a) => a.user !== o.user).map((a) => ({ label: a.name, onClick: () => bulk({ assigned_to: a.user }) })), { label: t('Unassign'), onClick: () => bulk({ assigned_to: '' }) }] },
        { label: t('Set status'), icon: 'refresh-cw', submenu: (o.statuses || []).map((x) => ({ label: t(x), onClick: () => bulk({ status: x }) })) },
        { label: t('Set priority'), icon: 'flag', submenu: (o.priorities || []).map((x) => ({ label: t(x), onClick: () => bulk({ priority: x }) })) },
      ],
    },
    { group: t('Share'), items: [{ label: t('Export as CSV'), icon: 'download', onClick: exportSelected }] },
  ]
  if (o.is_manager) groups.push({ group: t('Danger'), items: [{ label: t('Delete'), icon: 'trash-2', theme: 'red', onClick: () => (confirmDelete.value = true) }] })
  return groups
})

// Export the ticked rows as a spreadsheet file (CSV that Excel opens)
function exportSelected() {
  const rows = tickets.value.filter((r) => selected.value.includes(r.name))
  const cell = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const head = ['ID', 'Subject', 'Status', 'Priority', 'Type', 'Requester', 'Assigned to', 'Tags', 'Created', 'Respond by', 'Updated']
  const lines = rows.map((r) => [r.name, r.subject, r.status, r.priority, r.ticket_type, r.raised_by_name || r.raised_by, r.assigned_name || '', (r.tags || []).join('; '), r.creation, r.sla_due || '', r.modified].map(cell).join(','))
  const blob = new Blob(['\ufeff' + [head.map(cell).join(','), ...lines].join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `tickets-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
  toast.success(`${rows.length} ${t('tickets exported')}`)
}

const confirmDelete = ref(false)
async function doDelete() {
  try {
    const res = await deleteTickets([...selected.value])
    toast.success(`${res.deleted} ${t('tickets deleted')}`)
    confirmDelete.value = false
    selected.value = []
    load()
  } catch (e) {
    toast.error(String(e?.messages?.[0] || e?.message || t('The tickets could not be deleted.')).replace(/<[^>]+>/g, ''))
  }
}

let timer = null
watch([view, queueView, status, priority, type, sort, pageSize], () => {
  tickets.value = []
  load()
})
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
watch([view, queueView], () => router.replace({ query: view.value === 'mine' ? {} : { view: view.value, ...(view.value === 'queue' && queueView.value !== 'open' ? { q: queueView.value } : {}) } }))
onMounted(async () => {
  await loadSupportOptions()
  if (view.value !== 'mine' && !tabs.value.some((tab) => tab.key === view.value)) view.value = 'mine'
  load()
})
</script>
