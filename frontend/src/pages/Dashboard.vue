<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-medium text-gray-900 dark:text-gray-100">{{ greeting }}</h1>
      </template>
      <template #actions>
        <Dropdown :options="summaryExportOptions" placement="right">
          <Button variant="outline" icon-left="download" :disabled="!data">{{ t('Export') }}</Button>
        </Dropdown>
        <Button variant="ghost" icon="refresh-cw" :tooltip="t('Refresh')" :aria-label="t('Refresh')" :loading="dashboard.loading" @click="load" />
      </template>
    </PageHeader>

    <p v-if="data?.offline_as_of" class="mb-3 flex items-center gap-1.5 rounded-lg bg-surface-amber-1 px-3 py-2 text-sm text-ink-gray-7">
      <FeatherIcon name="wifi-off" class="h-4 w-4 flex-shrink-0 text-ink-amber-3" />
      {{ t('Offline copy - the numbers are as of your last download:') }} {{ data.offline_as_of }}
    </p>

    <!-- Filters -->
    <section class="dash-filters mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
      <FormControl type="select" class="w-full" :label="t('Partner organization')" :options="withAll(options?.partners)" v-model="filters.partner_organization" />
      <FormControl type="select" class="w-full" :label="t('Zone')" :options="withAll(options?.zones)" v-model="filters.zone" />
      <FormControl type="select" class="w-full" :label="t('Ward')" :options="withAll(options?.wards)" v-model="filters.ward" />
      <FormControl type="select" class="w-full" :label="t('Category')" :options="withAll(options?.categories)" v-model="filters.category" />
      <FormControl type="select" class="w-full" :label="t('Status')" :options="withAll(options?.validation_statuses)" v-model="filters.validation_status" />
      <div>
        <label class="mb-1.5 block text-xs text-ink-gray-5">{{ t('From') }}</label>
        <DatePicker class="w-full" format="DD MMM YYYY" v-model="filters.from_date" />
      </div>
      <div>
        <label class="mb-1.5 block text-xs text-ink-gray-5">{{ t('To') }}</label>
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
    <section class="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4" :aria-label="t('Key numbers')">
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
    <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">{{ t('Click any bar, slice or point to see the records.') }}</p>
    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard :title="t('Recorded over time')" :subtitle="t('Settlements profiled each month')" :empty="!data?.monthly?.length" :table="monthlyTable" class="lg:col-span-2">
        <DrillChart v-if="data?.monthly?.length" kind="line" :months="data.monthly.map((m) => m.month)" :series="monthlySeries" @select="onMonthly" />
      </ChartCard>

      <ChartCard v-for="chart in data?.charts || []" :key="chart.key" :title="t(chart.title)" :empty="!chart.rows.length" :table="tableOf(chart.rows)">
        <DrillChart
          v-if="chart.rows.length"
          :kind="chart.kind === 'donut' ? 'donut' : undefined"
          :horizontal="chart.kind === 'hbar'"
          :rows="chart.rows"
          @select="onRow(chart, $event)"
        />
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
import { t } from '@/utils/translate'
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
  partner_organization: '', zone: '', ward: '', category: '', validation_status: '', from_date: '', to_date: '',
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
  for (const chart of d.charts || []) for (const r of chart.rows) rows.push([chart.title, r.label, r.count])
  for (const r of d.monthly || []) rows.push(['Settlements per month', r.month, r.count])
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
const SETTLEMENT = 'Settlement'
const router = useRouter()
const DEFAULT_COLUMNS = {
  [SETTLEMENT]: ['settlement_name', 's1_zone', 's1_ward', 's2_total_households', 'validation_status'],
}
const show = ref(false)
const drillOpen = ref(false)
const drillKey = ref(0)
const drillTitle = ref('')
const drillDoctype = ref(SETTLEMENT)
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
const onRow = (chart, params) => {
  const row = chart.rows[params.dataIndex]
  if (row) drill(SETTLEMENT, row.filters, `${chart.title}: ${row.label}`)
}
function onMonthly(params) {
  const row = data.value?.monthly?.[params.dataIndex]
  if (row) drill(SETTLEMENT, row.filters, `${row.month} - Settlements`)
}

const tableOf = (rows) => ({ headers: ['Category', 'Settlements'], rows: (rows || []).map((r) => [r.label, r.count]) })
const monthlySeries = computed(() => [{ name: 'Settlements', values: (data.value?.monthly || []).map((m) => m.count) }])
const monthlyTable = computed(() => ({
  headers: ['Month', 'Settlements'],
  rows: (data.value?.monthly || []).map((m) => [m.month, m.count]),
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
