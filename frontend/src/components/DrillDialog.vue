<template>
  <Dialog v-model="open" :options="{ title, size: '5xl' }">
    <template #body-content>
      <!-- Toolbar: search, filter, sort, columns, export -->
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <div class="min-w-40 flex-1">
          <FormControl type="text" :placeholder="`Search by ${searchLabel.toLowerCase()}`" v-model="search" />
        </div>
        <Popover v-model:show="showFilter" placement="bottom-end" popover-class="doctype-list-popover" :hide-on-blur="false">
          <template #target="{ togglePopover }">
            <Button variant="outline" icon-left="filter" label="Filter" data-toolbar-popover-trigger @click="togglePopover">
              <template v-if="activeFilterCount" #suffix>
                <span class="flex h-4 min-w-4 items-center justify-center rounded-full bg-surface-gray-7 px-1 text-2xs text-ink-white">{{ activeFilterCount }}</span>
              </template>
            </Button>
          </template>
          <template #body-main>
            <div class="w-[26rem] max-w-[90vw] p-3">
              <FilterEditor :fields="allFields" v-model="advancedFilters" />
            </div>
          </template>
        </Popover>
        <SortControl v-model="sort" v-model:show="showSort" :fields="allFields" />
        <ColumnPicker v-model:show="showColumns" :prefs="columnPrefs" locked-label="ID" />
        <Dropdown v-if="canExport" :options="exportOptions" placement="right">
          <Button variant="solid" icon-left="download" :loading="exporting">Export</Button>
        </Dropdown>
      </div>

      <div class="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm text-gray-500 dark:text-gray-400">
        <span v-if="rowsCall.loading">Loading...</span>
        <span v-else>{{ total }} record{{ total === 1 ? '' : 's' }}</span>
        <Button v-if="activeFilterCount !== baseFilterCount || search" variant="ghost" size="sm" @click="resetFilters">Reset filters</Button>
      </div>
      <ErrorMessage v-if="rowsCall.error" class="mb-3" message="The records could not be loaded." />

      <div v-if="rows.length" class="max-h-[50vh] overflow-auto rounded-lg border dark:border-gray-800">
        <table class="w-full text-left text-sm">
          <thead class="sticky top-0 z-10 bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th class="whitespace-nowrap px-3 py-2 font-medium">ID</th>
              <th v-for="col in visibleColumns" :key="col.fieldname" class="whitespace-nowrap px-3 py-2 font-medium">{{ col.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.name"
              class="cursor-pointer border-t hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800"
              tabindex="0"
              @click="$emit('open-record', row.name)"
              @keydown.enter="$emit('open-record', row.name)"
            >
              <td class="whitespace-nowrap px-3 py-2 text-gray-800 dark:text-gray-200">{{ row.name }}</td>
              <td v-for="col in visibleColumns" :key="col.fieldname" class="px-3 py-2 text-gray-800 dark:text-gray-200">{{ cell(row, col) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="!rowsCall.loading" class="py-10 text-center text-sm text-gray-400">No records match.</div>

      <!-- Paging -->
      <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <span>Rows</span>
          <FormControl type="select" class="w-24" :options="PAGE_SIZES" v-model="pageSize" />
        </div>
        <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <span>{{ rangeLabel }}</span>
          <Button variant="outline" size="sm" icon="chevron-left" :disabled="page === 0 || rowsCall.loading" aria-label="Previous page" @click="page--" />
          <Button variant="outline" size="sm" icon="chevron-right" :disabled="(page + 1) * Number(pageSize) >= total || rowsCall.loading" aria-label="Next page" @click="page++" />
        </div>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <Button variant="subtle" @click="open = false">Close</Button>
        <Button variant="solid" @click="$emit('open-list', currentFilters)">Open full list</Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Dialog, Button, FormControl, Popover, Dropdown, ErrorMessage, toast, useCall } from 'frappe-ui'
import FilterEditor from '@/components/FilterEditor.vue'
import SortControl from '@/components/SortControl.vue'
import ColumnPicker from '@/components/ColumnPicker.vue'
import { useColumnPrefs } from '@/composables/useColumnPrefs'
import { useMeta, useFormFields } from '@/data/useMeta'
import { ensureTitlesForRows, linkTitle } from '@/data/linkTitles'

// The records behind a dashboard number or chart item: search, filter, sort, pick columns, page
// through them and download every match as CSV or Excel. Mount one per drill-down (`:key`), so it
// starts from `filters` each time.
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  doctype: { type: String, required: true },
  filters: { type: Object, default: () => ({}) },
  defaultColumns: { type: Array, default: () => [] },
  canExport: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'open-record', 'open-list'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const PAGE_SIZES = [10, 25, 50, 100].map((n) => ({ label: String(n), value: n }))
const metaResource = useMeta(props.doctype)
const allFields = useFormFields(metaResource)
const titleField = computed(() => metaResource.data?.title_field || 'name')
const searchLabel = computed(() => (titleField.value === 'name' ? 'ID' : allFields.value.find((f) => f.fieldname === titleField.value)?.label || 'name'))

const columnPrefs = useColumnPrefs({
  storageKey: `janadhikara-dashboard-columns-${props.doctype}`,
  allFields,
  defaultColumns: computed(() => props.defaultColumns.map((n) => allFields.value.find((f) => f.fieldname === n)).filter(Boolean)),
})
const visibleColumns = computed(() => columnPrefs.visibleColumns.value.filter((c) => c.fieldname !== 'name'))

const advancedFilters = ref({ ...props.filters })
const baseFilterCount = Object.keys(props.filters).length
const activeFilterCount = computed(() => Object.keys(advancedFilters.value).length)
const search = ref('')
const sort = ref({ field: 'modified', direction: 'desc' })
const page = ref(0)
const pageSize = ref(25)
const showFilter = ref(false)
const showSort = ref(false)
const showColumns = ref(false)

// The filter / sort / column popovers stay open until you click somewhere else (as on the list pages).
function closePopoversOnOutsideClick(event) {
  if (!showFilter.value && !showSort.value && !showColumns.value) return
  const target = event.target
  if (!(target instanceof Element)) return
  if (target.closest('.doctype-list-popover, [data-reka-popper-content-wrapper], [data-toolbar-popover-trigger]')) return
  // dropdowns opened from inside a popover render outside it - but the dialog itself is not one
  const content = target.closest('[data-slot="content"]')
  if (content && !content.closest('[role="dialog"]')) return
  showFilter.value = false
  showSort.value = false
  showColumns.value = false
}
watch(showFilter, (v) => { if (v) { showSort.value = false; showColumns.value = false } })
watch(showSort, (v) => { if (v) { showFilter.value = false; showColumns.value = false } })
watch(showColumns, (v) => { if (v) { showFilter.value = false; showSort.value = false } })
onMounted(() => document.addEventListener('pointerdown', closePopoversOnOutsideClick, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', closePopoversOnOutsideClick, true))

// Search matches the record's title (its name) as typed.
const currentFilters = computed(() => {
  const f = { ...advancedFilters.value }
  const text = search.value.trim()
  if (text) f[titleField.value] = ['like', `%${text}%`]
  return f
})
const orderBy = computed(() => `${sort.value.field} ${sort.value.direction}`)
function resetFilters() {
  advancedFilters.value = { ...props.filters }
  search.value = ''
}

const rows = ref([])
const total = ref(0)
const fetchFields = computed(() => ['name', ...visibleColumns.value.map((c) => c.fieldname)])
const rowsCall = useCall({
  url: `/api/v2/document/${props.doctype}`,
  method: 'GET',
  params: () => ({
    fields: JSON.stringify(fetchFields.value),
    filters: JSON.stringify(currentFilters.value),
    limit: Number(pageSize.value),
    start: page.value * Number(pageSize.value),
    order_by: orderBy.value,
  }),
  immediate: false,
  onSuccess: (data) => {
    rows.value = data || []
    ensureTitlesForRows(rows.value, visibleColumns.value.filter((c) => c.fieldtype === 'Link').map((c) => ({ fieldname: c.fieldname, fieldtype: 'Link', options: c.options })))
  },
})
const countCall = useCall({
  url: '/api/v2/method/frappe.client.get_count',
  method: 'GET',
  params: () => ({ doctype: props.doctype, filters: JSON.stringify(currentFilters.value) }),
  immediate: false,
  onSuccess: (n) => { total.value = n || 0 },
})

let timer
function reload({ resetPage = false } = {}) {
  if (resetPage && page.value !== 0) {
    page.value = 0 // the page watcher reloads
    return
  }
  clearTimeout(timer)
  timer = setTimeout(() => {
    rowsCall.fetch()
    countCall.fetch()
  }, 200)
}
// A new filter / search / page size starts again from the first page; a new page or sort only refetches rows.
watch([currentFilters, pageSize], () => reload({ resetPage: true }), { deep: true })
watch([sort, fetchFields], () => reload(), { deep: true })
watch(page, () => reload())
// Columns need the metadata first.
watch(() => metaResource.data, (meta) => { if (meta) reload() }, { immediate: true })

const rangeLabel = computed(() => {
  if (!total.value) return '0 of 0'
  const from = page.value * Number(pageSize.value) + 1
  return `${from}-${Math.min(total.value, from + rows.value.length - 1)} of ${total.value}`
})

function cell(row, col) {
  const value = row[col.fieldname]
  if (value == null || value === '') return '-'
  if (col.fieldtype === 'Check') return value ? 'Yes' : 'No'
  if (col.fieldtype === 'Link' && col.options) return linkTitle(col.options, value)
  return value
}

// Export: every match (not just this page) with the columns shown, in the sort order chosen.
const exporting = ref(false)
const exportOptions = [
  { label: 'CSV (.csv)', onClick: () => exportRecords('csv') },
  { label: 'Excel (.xlsx)', onClick: () => exportRecords('xlsx') },
]
async function exportRecords(format) {
  exporting.value = true
  try {
    const params = new URLSearchParams({
      doctype: props.doctype,
      filters: JSON.stringify(currentFilters.value),
      fields: JSON.stringify(visibleColumns.value.map((c) => c.fieldname)),
      order_by: orderBy.value,
      file_format: format,
    })
    const response = await fetch(`/api/method/janadhikara.dashboard.export_records?${params}`, { credentials: 'same-origin' })
    if (!response.ok) throw new Error(response.status === 403 ? 'You are not allowed to export these records.' : 'The export failed.')
    const blob = await response.blob()
    const disposition = response.headers.get('content-disposition') || ''
    const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] || `${props.doctype.toLowerCase().replace(/ /g, '_')}.${format}`
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(link.href)
    toast.success(`Exported ${total.value} record${total.value === 1 ? '' : 's'}`)
  } catch (error) {
    toast.error(error.message || 'The export failed.')
  } finally {
    exporting.value = false
  }
}
</script>
