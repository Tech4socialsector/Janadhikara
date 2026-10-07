<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-medium text-gray-900 dark:text-gray-100">{{ greeting }}</h1>
      </template>
      <template #actions>
        <Dropdown :options="summaryExportOptions" placement="right">
          <Button variant="outline" icon-left="download" :disabled="!data">Export</Button>
        </Dropdown>
        <Button variant="ghost" icon="refresh-cw" tooltip="Refresh" aria-label="Refresh" :loading="dashboard.loading" @click="load" />
      </template>
    </PageHeader>

    <!-- Filters -->
    <section class="dash-filters mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
      <FormControl type="select" class="w-full" label="Settlement" :options="withAll(options?.settlements)" v-model="filters.settlement" />
      <FormControl type="select" class="w-full" label="Partner organization" :options="withAll(options?.partners)" v-model="filters.partner_organization" />
      <FormControl type="select" class="w-full" label="Gender" :options="withAll(options?.genders)" v-model="filters.gender" />
      <FormControl type="select" class="w-full" label="Age group" :options="withAll(options?.age_groups)" v-model="filters.age_group" />
      <FormControl type="select" class="w-full" label="Household status" :options="withAll(options?.household_statuses)" v-model="filters.household_status" />
      <FormControl type="select" class="w-full" label="Documentation status" :options="withAll(options?.documentation_statuses)" v-model="filters.documentation_status" />
      <FormControl type="select" class="w-full" label="Validation status" :options="withAll(options?.validation_statuses)" v-model="filters.validation_status" />
      <div>
        <label class="mb-1.5 block text-xs text-ink-gray-5">From</label>
        <DatePicker class="w-full" format="DD MMM YYYY" v-model="filters.from_date" />
      </div>
      <div>
        <label class="mb-1.5 block text-xs text-ink-gray-5">To</label>
        <DatePicker class="w-full" format="DD MMM YYYY" v-model="filters.to_date" />
      </div>
      <div v-if="activeFilters" class="sm:col-span-2 lg:col-span-4 xl:col-span-5">
        <Button variant="ghost" size="sm" @click="clearFilters">
          <template #prefix><FeatherIcon name="x" class="h-3.5 w-3.5" /></template>
          Clear {{ activeFilters }} filter{{ activeFilters > 1 ? 's' : '' }}
        </Button>
      </div>
    </section>

    <ErrorMessage v-if="dashboard.error" class="mb-4" :message="dashboard.error?.messages?.[0] || 'The dashboard could not be loaded.'" />

    <!-- Number cards: click one to open the records behind it -->
    <section class="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Key numbers">
      <div v-for="i in (data ? 0 : 8)" :key="`s${i}`" class="h-[88px] animate-pulse rounded-xl border bg-gray-50 dark:border-gray-800 dark:bg-gray-900" />
      <button
        v-for="card in cards"
        :key="card.key"
        type="button"
        class="overflow-hidden rounded-xl border text-left transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:border-gray-800"
        :title="`Show ${card.title.toLowerCase()}`"
        @click="drill(card.doctype, card.filters, card.title)"
      >
        <NumberChart :config="{ title: card.title, value: card.value, suffix: card.suffix || undefined }" />
      </button>
    </section>

    <!-- Charts: click a bar, slice or point to open the records behind it -->
    <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">Click any bar, slice or point to see the records.</p>
    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title="Recorded over time" subtitle="Households and individuals added each month" :empty="!data?.monthly?.length" :table="monthlyTable" class="lg:col-span-2">
        <DrillChart v-if="data?.monthly?.length" kind="line" :months="data.monthly.map((m) => m.month)" :series="monthlySeries" @select="onMonthly" />
      </ChartCard>

      <ChartCard title="Household status" :empty="!data?.household_status?.length" :table="tableOf(data?.household_status, 'Households')">
        <DrillChart v-if="data?.household_status?.length" kind="donut" :rows="data.household_status" @select="onRow(HOUSEHOLD, data.household_status, $event)" />
      </ChartCard>
      <ChartCard title="Gender" :empty="!data?.gender?.length" :table="tableOf(data?.gender, 'Individuals')">
        <DrillChart v-if="data?.gender?.length" kind="donut" :rows="data.gender" @select="onRow(INDIVIDUAL, data.gender, $event)" />
      </ChartCard>

      <ChartCard title="Age groups" subtitle="Individuals by age (years)" :empty="!individualsTotal" :table="tableOf(data?.age_groups, 'Individuals')">
        <DrillChart v-if="individualsTotal" :rows="data.age_groups" @select="onRow(INDIVIDUAL, data.age_groups, $event)" />
      </ChartCard>
      <ChartCard title="Highest education" :empty="!data?.education?.length" :table="tableOf(data?.education, 'Individuals')">
        <DrillChart v-if="data?.education?.length" horizontal :rows="data.education" @select="onRow(INDIVIDUAL, data.education, $event)" />
      </ChartCard>

      <ChartCard title="Documents held" subtitle="Share of people asked who answered Yes" :empty="!hasDocuments" :table="documentsTable">
        <DrillChart v-if="hasDocuments" horizontal suffix="%" :max="100" series-name="Have it" :rows="data.documents" @select="onRow(INDIVIDUAL, data.documents, $event)" />
      </ChartCard>
      <ChartCard title="Main occupation" subtitle="Top 10" :empty="!data?.occupation?.length" :table="tableOf(data?.occupation, 'Individuals')">
        <DrillChart v-if="data?.occupation?.length" horizontal :rows="data.occupation" @select="onRow(INDIVIDUAL, data.occupation, $event)" />
      </ChartCard>

      <ChartCard title="Individual documentation" :empty="!individualsTotal" :table="tableOf(data?.documentation, 'Individuals')">
        <DrillChart v-if="individualsTotal" kind="donut" :rows="data.documentation" @select="onRow(INDIVIDUAL, data.documentation, $event)" />
      </ChartCard>
      <ChartCard title="Household documentation" :empty="!data?.household_documentation?.length" :table="tableOf(data?.household_documentation, 'Households')">
        <DrillChart v-if="data?.household_documentation?.length" kind="donut" :rows="data.household_documentation" @select="onRow(HOUSEHOLD, data.household_documentation, $event)" />
      </ChartCard>
    </section>

    <!-- Drill-down: the records behind a number or chart item, without leaving the dashboard -->
    <DrillDialog
      v-if="drillOpen"
      :key="drillKey"
      v-model="show"
      :title="drillTitle"
      :doctype="drillDoctype"
      :filters="drillFilters"
      :default-columns="DEFAULT_COLUMNS[drillDoctype]"
      :can-export="!!options?.can_export?.[drillDoctype]"
      @open-record="openRecord"
      @open-list="openList"
    />
  </AppLayout>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from 'vue'
import { NumberChart, Button, FormControl, DatePicker, FeatherIcon, ErrorMessage, Dropdown, toast, useCall } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import DrillChart from '@/components/DrillChart.vue'
import { findModuleByDoctype } from '@/data/modules'
import { session } from '@/data/session'
import { setPageTitle } from '@/data/pageTitle'
import DrillDialog from '@/components/DrillDialog.vue'
import { useRouter } from 'vue-router'

// A titled box around a chart, or a quiet "No data" note when there is nothing to draw. The small
// table button swaps the chart for its numbers (also the way to read the values without the pointer).
const ChartCard = defineComponent({
  props: { title: String, subtitle: String, empty: Boolean, table: Object },
  setup(props, { slots }) {
    const asTable = ref(false)
    const tableView = () =>
      h('div', { class: 'h-full overflow-auto' }, [
        h('table', { class: 'w-full text-left text-sm' }, [
          h('thead', h('tr', props.table.headers.map((th) => h('th', { class: 'px-2 py-1.5 text-xs font-medium uppercase text-gray-500 dark:text-gray-400' }, th)))),
          h('tbody', props.table.rows.map((row) =>
            h('tr', { class: 'border-t dark:border-gray-800' }, row.map((cell, i) =>
              h('td', { class: ['px-2 py-1.5 text-gray-800 dark:text-gray-200', i ? 'tabular-nums' : ''] }, String(cell)))))),
        ]),
      ])
    return () =>
      h('div', { class: 'overflow-hidden rounded-xl border bg-white p-4 dark:border-gray-800 dark:bg-gray-900' }, [
        h('div', { class: 'flex items-start justify-between gap-2' }, [
          h('div', [
            h('h2', { class: 'text-sm font-semibold text-gray-900 dark:text-gray-100' }, props.title),
            props.subtitle ? h('p', { class: 'text-xs text-gray-500 dark:text-gray-400' }, props.subtitle) : null,
          ]),
          props.table && !props.empty
            ? h('button', {
                type: 'button', class: 'rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800',
                title: asTable.value ? 'Show chart' : 'Show as table', 'aria-label': asTable.value ? 'Show chart' : 'Show as table',
                onClick: () => (asTable.value = !asTable.value),
              }, h(FeatherIcon, { name: asTable.value ? 'bar-chart-2' : 'list', class: 'h-4 w-4' }))
            : null,
        ]),
        h('div', { class: 'mt-3 h-72' },
          props.empty
            ? h('div', { class: 'flex h-full items-center justify-center text-sm text-gray-400' }, 'No data for these filters')
            : asTable.value && props.table ? tableView() : slots.default?.()),
      ])
  },
})

setPageTitle('Dashboard')

const greeting = computed(() => {
  const firstName = (session.full_name || '').split(' ')[0] || session.user
  return firstName ? `Welcome, ${firstName}` : 'Welcome'
})

const emptyFilters = () => ({
  settlement: '', partner_organization: '', gender: '', age_group: '', household_status: '', documentation_status: '',
  validation_status: '', from_date: '', to_date: '',
})
const filters = reactive(emptyFilters())
const activeFilters = computed(() => Object.values(filters).filter(Boolean).length)
function clearFilters() {
  Object.assign(filters, emptyFilters())
}

const optionsResource = useCall({ url: '/api/v2/method/janadhikara.dashboard.get_filter_options', method: 'GET', cacheKey: 'janadhikara-dashboard-filters' })
const options = computed(() => optionsResource.data)
// A select needs a way back to "everything".
const withAll = (list) => [
  { label: 'All', value: '' },
  ...(list || []).map((o) => (typeof o === 'string' ? { label: o, value: o } : o)),
]

const dashboard = useCall({
  url: '/api/v2/method/janadhikara.dashboard.get_dashboard',
  method: 'GET',
  params: () => Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
  immediate: false,
})
const data = computed(() => dashboard.data)
function load() {
  dashboard.fetch()
}
onMounted(load)
let timer
watch(filters, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})

const individualsTotal = computed(() => data.value?.cards?.individuals || 0)
const hasDocuments = computed(() => data.value?.documents?.some((d) => d.asked))

// Export of the dashboard itself: the numbers and every chart's values, as the filters currently show them.
const summaryExportOptions = [
  { label: 'Summary (CSV)', onClick: exportSummary },
]
function exportSummary() {
  const d = data.value
  if (!d) return
  const rows = [['Section', 'Item', 'Value']]
  const applied = Object.entries(filters).filter(([, v]) => v).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join('; ')
  rows.push(['Filters', applied || 'None', ''])
  for (const c of d.cards) rows.push(['Numbers', c.title, `${c.value}${c.suffix || ''}`])
  const groups = [
    ['Household status', d.household_status], ['Household documentation', d.household_documentation], ['Gender', d.gender],
    ['Age groups', d.age_groups], ['Highest education', d.education], ['Individual documentation', d.documentation], ['Main occupation', d.occupation],
  ]
  for (const [name, list] of groups) for (const r of list || []) rows.push([name, r.label, r.count])
  for (const r of d.documents || []) rows.push(['Documents held (%)', r.label, r.percent])
  for (const r of d.monthly || []) { rows.push(['Households per month', r.month, r.Households]); rows.push(['Individuals per month', r.month, r.Individuals]) }
  const text = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""').replace(/^([=+\-@])/, "'$1")}"`).join(',')).join('\r\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8' }))
  link.download = `dashboard_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(link.href)
  toast.success('Dashboard summary exported')
}

const cards = computed(() => data.value?.cards || [])

// Drill down: open a doctype's list already filtered to what was clicked.
const HOUSEHOLD = 'Household Profile'
const INDIVIDUAL = 'Individual Profile'
const router = useRouter()
const DEFAULT_COLUMNS = {
  [HOUSEHOLD]: ['respondent_name', 'settlement', 'household_status', 'status'],
  [INDIVIDUAL]: ['member_name', 'gender', 'age', 'household', 'documentation_status'],
}
const show = ref(false)
const drillOpen = ref(false)
const drillKey = ref(0)
const drillTitle = ref('')
const drillDoctype = ref(HOUSEHOLD)
const drillFilters = ref({})

// Drill down: the records behind a number or chart item, in a popup.
function drill(doctype, filters, title) {
  drillDoctype.value = doctype
  drillFilters.value = filters || {}
  drillTitle.value = title || doctype
  drillKey.value += 1 // a fresh popup each time, starting from these filters
  drillOpen.value = true
  show.value = true
}
function openRecord(name) {
  const route = findModuleByDoctype(drillDoctype.value)?.route
  if (route) router.push({ name: 'DoctypeForm', params: { doctypeRoute: route, name } })
}
function openList(filters) {
  const route = findModuleByDoctype(drillDoctype.value)?.route
  if (route) router.push({ name: 'DoctypeList', params: { doctypeRoute: route }, query: { filters: JSON.stringify(filters || {}) } })
}
const unit = (doctype) => (doctype === HOUSEHOLD ? 'Households' : 'Individuals')
const onRow = (doctype, rows, params) => {
  const row = rows[params.dataIndex]
  if (row) drill(doctype, row.filters, `${row.label} - ${unit(doctype)}`)
}
function onMonthly(params) {
  const row = data.value?.monthly?.[params.dataIndex]
  if (!row) return
  if (params.seriesName === 'Households') drill(HOUSEHOLD, row.household_filters, `${row.month} - Households`)
  else drill(INDIVIDUAL, row.individual_filters, `${row.month} - Individuals`)
}

const tableOf = (rows, unit) => ({ headers: ['Category', unit], rows: (rows || []).map((r) => [r.label, r.count]) })
const documentsTable = computed(() => ({
  headers: ['Document', 'Have it (%)', 'Have it', 'Asked'],
  rows: (data.value?.documents || []).map((d) => [d.label, d.percent, d.have, d.asked]),
}))
const monthlySeries = computed(() => [
  { name: 'Households', values: (data.value?.monthly || []).map((m) => m.Households) },
  { name: 'Individuals', values: (data.value?.monthly || []).map((m) => m.Individuals) },
])
const monthlyTable = computed(() => ({
  headers: ['Month', 'Households', 'Individuals'],
  rows: (data.value?.monthly || []).map((m) => [m.month, m.Households, m.Individuals]),
}))
</script>

<style scoped>
/* Every filter - dropdowns and date pickers alike - fills its grid cell and is the same height. */
.dash-filters :deep([data-slot='trigger']),
.dash-filters :deep(input),
.dash-filters :deep(button[role='combobox']) {
  width: 100%;
  height: 2rem;
  min-height: 2rem;
}
.dash-filters :deep(.w-full),
.dash-filters :deep([data-slot='root']) {
  width: 100%;
}
</style>
