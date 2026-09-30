<template>
  <div>
    <div class="mb-2 flex items-center justify-between gap-3">
      <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ field.label }}</h3>
      <Button variant="ghost" @click="addRow">
        <template #prefix>
          <FeatherIcon name="plus" class="h-4 w-4" />
        </template>
        Add Row
      </Button>
    </div>

    <!-- Generic, doctype-agnostic quick filter - every child table in the
    app gets this the same way, since it only ever depends on
    summaryColumns/formatValue, both already computed per-child-doctype
    from its own metadata. Client-side substring match, not a server
    round-trip: a child table's rows already live entirely in memory (the
    parent document's own field value), there is no "fetch a filtered
    page" concept here the way DoctypeList.vue's own list has - narrowing
    what's already loaded is the whole job. Hidden when there's nothing
    worth filtering (0-1 rows) rather than always-on chrome for an
    almost-always-short list. -->
    <div v-if="rows.length > 1" class="relative mb-2">
      <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search rows"
        class="h-8 w-full rounded-md border border-gray-200 bg-white pl-8 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-300 focus:outline-none focus:ring-1 focus:ring-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500"
      />
    </div>

    <!-- Same frappe-ui ListView grid DoctypeList.vue's main list uses (see
    that file for the full reasoning) - borderless rows (only the header's
    own bottom border), row hover highlight, no vertical grid lines,
    checkbox column + floating select-banner for bulk delete. Each row
    also keeps an Edit icon plus a "..." menu (Duplicate, Insert Above,
    Insert Below, Remove) via ListRowItem's #suffix slot on the last
    column, matching Frappe Desk's own child-table grid row actions -
    always visible rather than hover-revealed, since ListRow.vue has no
    `group` class on its own row wrapper to hook a group-hover off of.

    Default slot overridden (reproducing ListView.vue's own fallback
    content: ListHeader/ListRows/ListGroups/ListEmptyState/
    ListSelectBanner) only so ListSelectBanner can get a custom #actions
    (a Delete button) - its own bare default has no bulk-delete action,
    just Select all/dismiss. An earlier version tried adding a second,
    hand-built "N selected" bar alongside ListView's own auto-rendered
    banner instead of doing this - confirmed live that produces two
    separate "selected" banners on screen at once. -->
    <ListView
      :columns="listViewColumns"
      :rows="filteredRows"
      row-key="__key"
      :options="listViewOptions"
      @update:selections="(sel) => (selectedKeys = Array.from(sel))"
    >
      <template #cell="{ column, row, item }">
        <ListRowItem :column="column" :row="row" :item="formatValue(item, column.docField)">
          <template v-if="column.key === lastColumnKey" #suffix>
            <div class="ml-auto flex items-center gap-1" @click.stop>
              <Tooltip text="Edit row">
                <button
                  type="button"
                  class="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                  @click="openRow(rows.indexOf(row))"
                >
                  <FeatherIcon name="edit-2" class="h-4 w-4" />
                </button>
              </Tooltip>
              <Dropdown placement="bottom-end" :options="rowActions(rows.indexOf(row))">
                <template #default="{ open }">
                  <button
                    type="button"
                    class="flex h-7 w-7 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                    :class="{ 'bg-gray-100 dark:bg-gray-800': open }"
                  >
                    <FeatherIcon name="more-horizontal" class="h-4 w-4" />
                  </button>
                </template>
              </Dropdown>
            </div>
          </template>
        </ListRowItem>
      </template>
      <template #default="{ showGroupedRows, selectable }">
        <ListHeader />
        <template v-if="filteredRows.length">
          <ListGroups v-if="showGroupedRows" />
          <ListRows v-else />
        </template>
        <!-- Rows exist but the search box filtered all of them out - a
        distinct message from ListEmptyState's own "No rows yet" (still
        used, unchanged, for the genuinely-empty case), so clearing the
        search is obviously the way back rather than looking like the
        whole table just emptied itself. -->
        <div v-else-if="searchQuery" class="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
          No rows match "{{ searchQuery }}".
        </div>
        <ListEmptyState v-else />
        <ListSelectBanner v-if="selectable">
          <template #actions>
            <Button variant="solid" theme="red" @click="confirmBulkRemove">
              <template #prefix>
                <FeatherIcon name="trash-2" class="h-4 w-4" />
              </template>
              Delete
            </Button>
          </template>
        </ListSelectBanner>
      </template>
    </ListView>

    <Dialog v-model="showRowEditor" :options="{ size: '2xl', title: 'row-editor' }">
      <template #body>
        <!-- #body-content (the default slot this used before) sits inside
        Dialog's own fixed-padding, non-scrollable wrapper alongside the
        header - fine for a couple of fields, but a child doctype with 15+
        fields (ANC Followup, for one) just grew the dialog past the
        viewport with no scroll of its own, spilling content off-screen
        with only the page behind it able to scroll. Taking over #body
        entirely (same pattern as SettingsDialog.vue/AiAssistant.vue) is
        the only way to give the field list its own scroll region instead. -->
        <div class="row-editor-panel flex flex-col" :style="{ height: editorHeight }">
          <div class="flex h-12 flex-shrink-0 items-center justify-between border-b px-4 dark:border-gray-800 sm:px-6">
            <h3 class="truncate text-base font-semibold text-gray-900 dark:text-gray-100">
              {{ field.label }} - Row {{ (editingIdx ?? 0) + 1 }}
            </h3>
            <button
              class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
              @click="showRowEditor = false"
            >
              <FeatherIcon name="x" class="h-4 w-4" />
            </button>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            <div v-if="editingRow" class="grid grid-cols-1 gap-4">
              <DynamicField
                v-for="col in columns"
                :key="col.fieldname"
                :field="col"
                :doctype="doctype"
                :docname="docname"
                :sibling-values="editingRow"
                v-model="editingRow[col.fieldname]"
              />
            </div>
          </div>

          <div class="flex-shrink-0 border-t p-4 dark:border-gray-800">
            <Button variant="solid" class="w-full" @click="showRowEditor = false">
              Done
            </Button>
          </div>
        </div>
      </template>
    </Dialog>

    <Dialog
      v-model="showRemoveConfirm"
      :options="{
        title: pendingRemoveIndices.length > 1 ? `Remove ${pendingRemoveIndices.length} rows?` : 'Remove row?',
        message: 'This cannot be undone once you save the form.',
        icon: { name: 'alert-triangle', appearance: 'danger' },
        actions: [
          { label: 'Remove', variant: 'solid', theme: 'red', onClick: doRemoveRow },
          { label: 'Cancel' },
        ],
      }"
    />
  </div>
</template>

<style>
/* Same data-dialog/[title] hook as SettingsDialog.vue/AiAssistant.vue -
frappe-ui's Dialog has no size option granular enough for "scales with
the viewport, full-screen on mobile" on its own. Sized a bit taller than
SettingsDialog's 34rem/80vh since child-table rows here can run to 15+
fields (ANC Followup) - the request was explicitly for a bigger popup,
scaled to screen size rather than a fixed height regardless of viewport. */
/* 1050, not 50: Leaflet's own stylesheet puts its control pane (zoom
buttons etc.) at z-index 1000, and a page behind this dialog (or a
Geolocation field on the row itself) can have a Leaflet map - at 50 the
map's controls would paint through this dialog instead of being covered
by it. */
[data-dialog='row-editor'].dialog-overlay {
  z-index: 1050;
}

.row-editor-panel {
  width: 100%;
  max-height: 85vh;
}

@media (max-width: 639px), (max-height: 480px) {
  [data-dialog='row-editor'].dialog-overlay > div {
    padding: 0;
  }
  [data-dialog='row-editor'] .dialog-content {
    margin: 0;
    max-width: none;
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }
  .row-editor-panel {
    /* !important: the panel's height is otherwise set inline (bound to
    editorHeight, sized to the row's own field count/types) - inline
    style specificity always wins over a class selector regardless of
    cascade order, so without this a content-sized popup on desktop would
    carry its short/tall inline height straight into the mobile
    full-screen layout instead of actually filling the screen. */
    height: 100dvh !important;
    max-height: none;
  }
}
</style>

<script setup>
import { computed, ref } from 'vue'
import {
  Button,
  FeatherIcon,
  Dialog,
  Dropdown,
  ListView,
  ListHeader,
  ListRows,
  ListRowItem,
  ListGroups,
  ListEmptyState,
  ListSelectBanner,
  Tooltip,
} from 'frappe-ui'
import DynamicField from '@/components/DynamicField.vue'
import { useMeta, useFormFields } from '@/data/useMeta'

const { field, modelValue, doctype, docname } = defineProps({
  field: { type: Object, required: true },
  modelValue: { type: Array, default: () => [] },
  doctype: { type: String, default: null },
  docname: { type: String, default: null },
})
const emit = defineEmits(['update:modelValue'])

const childMetaResource = useMeta(field.options)
const columns = useFormFields(childMetaResource)

// The row summary in the table only needs enough columns to identify the
// row at a glance - matching Desk's grid, which shows a handful of
// in_list_view fields and pushes the rest behind the row-edit dialog. Wide
// child tables (10+ fields) are unusable as an all-columns-inline table.
const summaryColumns = computed(() => {
  const inListView = columns.value.filter((c) => c.in_list_view)
  return (inListView.length ? inListView : columns.value).slice(0, 3)
})

// Same column shape DoctypeList.vue builds for its own ListView - key/
// label for ListView itself, docField keeping the original Frappe field
// object attached so formatValue (which expects that shape) still works
// from inside the #cell slot.
const listViewColumns = computed(() =>
  summaryColumns.value.map((col) => ({
    key: col.fieldname,
    label: col.label,
    docField: col,
  })),
)
// The Edit/"..." menu buttons render as the #suffix of whichever column
// is rendered last, so they land at the right edge of the row instead of
// needing a separate dedicated actions column (ListView has no built-in
// concept of one).
const lastColumnKey = computed(() => listViewColumns.value.at(-1)?.key)

const selectedKeys = ref([])
const listViewOptions = computed(() => ({
  selectable: true,
  showTooltip: false,
  onRowClick: (row) => openRow(rows.value.indexOf(row)),
  emptyState: { title: 'No rows yet' },
}))

// Popup height driven by this row's own field count/types instead of a
// flat 42rem for every child doctype regardless of size - a 1-field child
// (AI Guide Instruction) gets a compact popup that hugs its single field
// instead of a tall mostly-empty box, while a 15+ field one (ANC Followup)
// still gets the previous roomy, scrollable treatment. Approximate per
// row-height only (not a real layout measurement) since this has to be
// known before the dialog/fields ever paint - close enough for a popup
// size, not meant to be pixel-exact.
const TALL_FIELDTYPES = new Set(['Text Editor', 'Small Text', 'Text', 'Long Text', 'Code', 'HTML Editor', 'Attach Image', 'Attach'])
const ROW_HEIGHT_REM = 4.5
const TALL_ROW_HEIGHT_REM = 8
const CHROME_HEIGHT_REM = 9.5 // header + footer + vertical padding
const MIN_PANEL_HEIGHT_REM = 14
const MAX_PANEL_HEIGHT_REM = 42

const editorHeight = computed(() => {
  const fieldsHeight = columns.value.reduce(
    (sum, col) => sum + (TALL_FIELDTYPES.has(col.fieldtype) ? TALL_ROW_HEIGHT_REM : ROW_HEIGHT_REM),
    0,
  )
  const total = Math.min(MAX_PANEL_HEIGHT_REM, Math.max(MIN_PANEL_HEIGHT_REM, fieldsHeight + CHROME_HEIGHT_REM))
  return `${total}rem`
})

let rowKeyCounter = 0
const rows = computed({
  // Every row needs a stable, unique __key for ListView's row-key to
  // actually distinguish rows (selection, v-for identity) - a row loaded
  // from a saved document already has a real unique id in its own `name`
  // field (Frappe assigns child-table rows a name on save, confirmed via
  // bench execute: e.g. "cmlvqrehjj"), but a brand-new row added via
  // addRow/insertRowAt has neither `name` nor `__key` yet. Backfilling
  // __key here (mutating the row in place, not replacing it - same
  // identity-preserving reasoning as addRow's own in-place push below)
  // means every row that ever reaches ListView has one, whether it came
  // from the server or was created client-side a moment ago. Without
  // this, every row missing __key shared the literal value `undefined`,
  // so selecting any one of them visually selected all of them at once
  // (confirmed live) - Set.has(undefined) matched every row with no key.
  get: () => {
    const list = modelValue || []
    for (const row of list) {
      if (!row.__key) row.__key = row.name || `new-${rowKeyCounter++}`
    }
    return list
  },
  set: (v) => emit('update:modelValue', v),
})

// Generic quick filter - matches formatValue's own display text (not the
// raw stored value), same as what's actually visible in the grid, across
// every summary column currently shown. Deliberately not saved/persisted
// anywhere and reset per doctype-agnostic reasoning: this is a transient
// "find a row on screen" aid, not a real query a user would expect to
// come back later, unlike DoctypeList.vue's own quick filters (which do
// persist, because those actually change what's fetched from the
// server).
const searchQuery = ref('')
const filteredRows = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return rows.value
  return rows.value.filter((row) =>
    summaryColumns.value.some((col) => formatValue(row[col.fieldname], col).toLowerCase().includes(query)),
  )
})

function addRow() {
  // Mutate the array in place (it's the same reactive array the parent form
  // owns) rather than reassigning through the computed setter - reassigning
  // round-trips through the parent via emit('update:modelValue', ...), and
  // reading rows.value.length right after that in the same tick can still
  // see the pre-update array, opening the row editor on the wrong (stale)
  // index.
  const newRow = { __key: `new-${rowKeyCounter++}` }
  rows.value.push(newRow)
  openRow(rows.value.indexOf(newRow))
}

// A row's own text column has nowhere to shrink to make room for the
// Edit/Remove suffix icons - ListRowItem's inner flex row (frappe-ui,
// not overridable from here) has no min-width: 0, and ListView's grid
// tracks are plain 1fr rather than minmax(0, 1fr), so neither layer
// actually enforces the "truncate" class it puts on the label; a long
// value just grows the row past the icons instead (confirmed live: the
// buttons render correctly in the DOM, just pushed off past the visible
// row width). Truncating the string itself here is the only reliable fix
// without forking those components.
const SUMMARY_VALUE_MAX_LENGTH = 60
function formatValue(value, field) {
  if (value == null || value === '') return '-'
  if (field.fieldtype === 'Check') return value ? 'Yes' : 'No'
  const text = String(value)
  return text.length > SUMMARY_VALUE_MAX_LENGTH ? text.slice(0, SUMMARY_VALUE_MAX_LENGTH - 1) + '…' : text
}

const showRowEditor = ref(false)
const editingIdx = ref(null)
const editingRow = computed(() => (editingIdx.value == null ? null : rows.value[editingIdx.value]))

function openRow(idx) {
  editingIdx.value = idx
  showRowEditor.value = true
}

const showRemoveConfirm = ref(false)
// Always an array (even for a single row) - doRemoveRow doesn't need two
// branches for "remove one" vs "remove several", just one filter either
// way. selectedKeys (the ListView checkbox selection) is separate from
// this - it's cleared once removal actually happens, not the moment the
// confirm dialog opens, so cancelling a bulk remove doesn't lose the
// user's selection.
const pendingRemoveIndices = ref([])

function confirmRemoveRow(idx) {
  pendingRemoveIndices.value = [idx]
  showRemoveConfirm.value = true
}

function confirmBulkRemove() {
  pendingRemoveIndices.value = selectedKeys.value
    .map((key) => rows.value.findIndex((r) => r.__key === key))
    .filter((idx) => idx !== -1)
  showRemoveConfirm.value = true
}

function doRemoveRow(close) {
  const toRemove = new Set(pendingRemoveIndices.value)
  rows.value = rows.value.filter((_, i) => !toRemove.has(i))
  pendingRemoveIndices.value = []
  selectedKeys.value = []
  close()
}

// Same in-place splice + open pattern as addRow above, and for the same
// reason: reassigning rows.value (as doRemoveRow/confirmBulkRemove do)
// round-trips through the parent via emit('update:modelValue', ...), and
// reading the new row's index right after that in the same tick can
// still see the pre-update array - splicing the live array in place and
// reading its index immediately after avoids that race, letting Duplicate/
// Insert Above/Insert Below open their new row's editor right away, the
// same as Add Row already does.
function insertRowAt(idx, values = {}) {
  const row = { ...values, __key: `new-${rowKeyCounter++}` }
  rows.value.splice(idx, 0, row)
  openRow(rows.value.indexOf(row))
}

// Clones every field value except __key (a fresh one is assigned so the
// copy is a distinct row, not a reactive alias of the original) - inserted
// directly after the source row, matching Frappe Desk's own "Duplicate
// Row" placement.
function duplicateRow(idx) {
  const source = rows.value[idx]
  if (!source) return
  const { __key, ...values } = source
  insertRowAt(idx + 1, values)
}

function insertRowAbove(idx) {
  insertRowAt(idx)
}

function insertRowBelow(idx) {
  insertRowAt(idx + 1)
}

// Dropdown options for a row's "..." menu (Duplicate/Insert Above/Insert
// Below/Remove) - matching Frappe Desk's own child-table grid row context
// menu. idx is resolved fresh on each click (rows.indexOf(row) at the
// call site in the template) rather than captured here, since inserting/
// duplicating earlier rows shifts every later row's index.
function rowActions(idx) {
  return [
    {
      group: 'Row',
      items: [
        { label: 'Duplicate', icon: 'copy', onClick: () => duplicateRow(idx) },
        { label: 'Insert Above', icon: 'arrow-up', onClick: () => insertRowAbove(idx) },
        { label: 'Insert Below', icon: 'arrow-down', onClick: () => insertRowBelow(idx) },
      ],
    },
    {
      group: 'Remove',
      items: [
        { label: 'Remove', icon: 'trash-2', theme: 'red', onClick: () => confirmRemoveRow(idx) },
      ],
    },
  ]
}
</script>
