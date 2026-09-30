<template>
  <div>
    <label class="mb-1.5 block text-sm text-gray-700 dark:text-gray-300">
      {{ field.label }}<span v-if="field.reqd" class="text-red-500">*</span>
    </label>
    <div class="flex items-center gap-1.5">
      <div class="link-field-combobox min-w-0 flex-1">
        <Combobox
          open-on-focus
          open-on-click
          :options="options"
          :loading="recordsResource.loading"
          :disabled="disabled"
          :placeholder="filtersPending ? 'Select a value above first' : `Select ${field.label}`"
          :model-value="modelValue"
          @update:model-value="(value) => $emit('update:modelValue', value || null)"
        />
      </div>
      <Tooltip v-if="linkedRoute" :text="`Open ${field.label}`">
        <button
          type="button"
          class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200"
          @click="openLinkedRecord"
        >
          <FeatherIcon name="arrow-up-right" class="h-4 w-4" />
        </button>
      </Tooltip>
      <!-- Extension point for a caller-supplied affordance next to the
      combobox - currently only DynamicField.vue's isUserLink case (a
      UserLinkHoverCard quick-preview), which linkedRoute above can never
      cover: User is a core Frappe doctype, never registered in an App
      Module Setting, so "Open" here never appears for it regardless of
      what's picked. Kept generic (not literally "user-preview") since any
      future Link field might reasonably want its own inline affordance
      the same way. -->
      <slot name="suffix" />
    </div>
    <p v-if="field.description" class="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
      {{ field.description }}
    </p>

    <Dialog v-model="showCreateDialog" :options="{ size: 'lg', title: 'link-quick-create' }">
      <template #body>
        <div class="link-quick-create-panel flex flex-col">
          <div class="flex h-12 flex-shrink-0 items-center justify-between border-b px-4 dark:border-gray-800">
            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
              New {{ field.options }}
            </h3>
            <button
              class="flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
              @click="showCreateDialog = false"
            >
              <FeatherIcon name="x" class="h-4 w-4" />
            </button>
          </div>

          <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
            <div v-if="isPromptNamed">
              <FormControl type="text" label="Name" required v-model="newRecordName" />
            </div>
            <DynamicField
              v-for="createField in createFields"
              :key="createField.fieldname"
              :field="createField"
              :doctype="field.options"
              v-model="newRecordValues[createField.fieldname]"
            />
            <ErrorMessage :message="createError" />
          </div>

          <div class="flex flex-shrink-0 justify-end gap-2 border-t p-4 dark:border-gray-800">
            <Button @click="showCreateDialog = false">Cancel</Button>
            <Button variant="solid" :loading="creating" @click="submitNewRecord">Create</Button>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
/* Combobox's own trigger (a ComboboxAnchor, styled as a text-input-shaped
box in "input" trigger mode) doesn't fill this field on its own - reka-ui
renders it a few levels deep from this component's own flex container,
and without an explicit width the whole chain shrinks to content size
instead of resolving "100%" to something real. Every ancestor down to the
actual trigger element needs an explicit block/full width for that to
work, which is why every Link field's dropdown used to render at a
different width per its own label/value text length instead of filling
its column like every other field type. */
.link-field-combobox :deep(> div) {
  display: block;
  width: 100%;
}
.link-field-combobox :deep([data-slot='trigger']) {
  width: 100%;
}
</style>

<style>
/* Same data-dialog hook pattern as ChildTable.vue's row editor/
SettingsDialog.vue - takes over #body entirely (frappe-ui's default
#body-content wrapper has no independent scroll region) so a linked
doctype with many fields still scrolls inside the dialog instead of
overflowing past it. */
/* 1050, not 50: Leaflet's own stylesheet puts its control pane (zoom
buttons etc.) at z-index 1000, and this dialog can open on top of a page
that already has a Geo Location map on it (e.g. this quick-create, opened
from a Link field on a form that also has a map) - at 50 the map's
controls painted through the dialog instead of being covered by it. */
[data-dialog='link-quick-create'].dialog-overlay {
  z-index: 1050;
}
.link-quick-create-panel {
  width: 100%;
  height: 32rem;
  max-height: 85vh;
}
@media (max-width: 639px), (max-height: 480px) {
  [data-dialog='link-quick-create'].dialog-overlay > div {
    padding: 0;
  }
  [data-dialog='link-quick-create'] .dialog-content {
    margin: 0;
    max-width: none;
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }
  .link-quick-create-panel {
    height: 100dvh;
    max-height: none;
  }
}
</style>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Combobox, Dialog, Button, ErrorMessage, FeatherIcon, FormControl, Tooltip, call, useCall, toast } from 'frappe-ui'
import { findModuleByDoctype } from '@/data/modules'
import DynamicField from '@/components/DynamicField.vue'

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null },
  // Extra Frappe filters applied server-side (e.g. District filtered by the
  // currently selected State) - a plain object of {fieldname: value}, ANDed
  // together, matching frappe.client.get_list's filters shape.
  filters: { type: Object, default: () => ({}) },
  // Used on list-view filter bars (desktop row and the mobile filter
  // sheet), where "no value picked" is itself a valid, meaningful choice
  // ("All Villages") rather than an incomplete required field - adds that
  // as a selectable option instead of just leaving the field blank with no
  // way back to "unfiltered" short of a separate Clear button.
  allowClear: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

// The linked doctype's own title_field (if set) is what a user actually
// recognizes a record by - falling back to `name` (Frappe's own default
// display rule) when the doctype doesn't define one.
const metaResource = useCall({
  url: `/api/v2/doctype/${props.field.options}/meta`,
  method: 'GET',
  cacheKey: `janadhikara-meta-${props.field.options}`,
})
const titleField = computed(() => metaResource.data?.title_field || 'name')

// A cascading filter (e.g. District's `state`) resolves to undefined/null
// until the field it depends on is actually filled in - fetching with that
// missing means "no filter" server-side, which would show every District
// instead of none, letting a user pick one that doesn't match their State.
const filtersPending = computed(() => Object.values(props.filters).some((v) => v == null || v === ''))

// useCall's `url` is passed through Vue's unref() internally, which only
// unwraps a ref/computed - a plain arrow function (the pattern used
// elsewhere in this codebase, e.g. TableMultiSelectField.vue) is returned
// as-is and gets template-string-stringified into the request path, never
// actually invoked. A computed() is what unref() actually resolves.
const recordsUrl = computed(() => `/api/v2/document/${props.field.options}`)

const recordsResource = useCall({
  url: recordsUrl,
  method: 'GET',
  params: () => ({
    fields: JSON.stringify(['name', titleField.value]),
    filters: JSON.stringify(props.filters),
    // Same "large fixed limit stands in for effectively all" reasoning as
    // TableMultiSelectField - these are bounded master/lookup lists, not a
    // paged view, and the v2 API has no unlimited sentinel.
    limit: 1000,
  }),
  immediate: false,
})

// Re-fetch whenever the doctype or the cascading filters change (e.g.
// District's State filter) - a stale options list from before the filter
// changed would let a value get picked that no longer matches. Gated on
// metaResource.data being loaded (rather than firing immediately at
// mount) so the very first records fetch already has the doctype's real
// title_field - firing immediately with titleField's fallback ('name')
// and correcting it once metaResource resolves used to mean two fetches
// back-to-back, the second silently aborting the first (harmless, but
// noisy: "AbortError: The user aborted a request" in the console on
// every single Link field, every time its containing form loads).
watch(
  () => [props.field.options, JSON.stringify(props.filters), filtersPending.value, !!metaResource.data],
  () => {
    if (props.field.options && !filtersPending.value && metaResource.data) recordsResource.fetch()
  },
  { immediate: true },
)

// Frappe desk only offers "Create a New X" from a Link field when the
// current user actually holds create permission on that doctype (role-based,
// same as everywhere else in Desk) - frappe.client.has_permission is the
// standard whitelisted check for exactly this, evaluated server-side so it
// reflects the full permission system (roles, user permissions, etc.)
// rather than reimplementing that logic here. docname is a required
// parameter of the endpoint but irrelevant for a doctype-level "create"
// check, so it's passed empty.
const createPermissionResource = useCall({
  url: '/api/v2/method/frappe.client.has_permission',
  method: 'GET',
  params: () => ({ doctype: props.field.options, docname: '', perm_type: 'create' }),
  immediate: false,
  transform: (data) => data?.has_permission,
})
watch(
  () => props.field.options,
  (doctype) => {
    if (doctype) createPermissionResource.fetch()
  },
  { immediate: true },
)
const canCreate = computed(() => !!createPermissionResource.data)

const options = computed(() => {
  if (filtersPending.value) return []
  const rows = recordsResource.data || []
  // r.name is coerced to a string - a doctype named with autoname:
  // "autoincrement" (e.g. District) comes back from the API as a JSON
  // number (6, not "6"), while modelValue (whatever's actually stored on
  // the referencing doc, and whatever Combobox's own v-model carries) is
  // always a string. Combobox matches modelValue against each option's
  // `value` by strict equality to resolve which option is "selected" and
  // show its label - a number 6 vs string "6" never matches, so a
  // perfectly valid, already-linked record would resolve to no matching
  // option and Combobox would fall back to displaying the raw stored
  // value instead of the record's title_field label.
  const opts = rows.map((r) => ({ label: r[titleField.value] || r.name, value: String(r.name) }))
  if (props.allowClear) {
    opts.unshift({ label: `All ${props.field.label}`, value: '' })
  } else {
    // Every Link (not just a non-mandatory one) needs a real way back to
    // "no value" once something's been picked - Frappe desk's own Link
    // field allows clearing for exactly this reason, and a required field
    // being clearable while editing doesn't mean it's savable empty; that
    // stays enforced at save time same as ever. Matches DynamicField.vue's
    // own Select fields, which get the same unconditional "Select option"
    // entry.
    opts.unshift({ label: 'Select option', value: '' })
  }
  // Not offered on filter bars (allowClear) - "create a record" doesn't
  // belong in a "narrow this list down" control, and filtersPending means
  // there's nothing meaningful to create against yet anyway.
  if (canCreate.value && !props.allowClear && !filtersPending.value) {
    opts.push({
      type: 'custom',
      key: '__create__',
      label: `+ Create New ${props.field.label}`,
      condition: () => true,
      onClick: openCreateDialog,
    })
  }
  return opts
})

// Frappe desk's Link field always shows an arrow to open the linked
// record directly - this app's generic /:doctypeRoute/:name route can only
// resolve a doctype that's actually registered in an App Module Setting
// (see findModuleByDoctype), so the icon only appears when that's true
// rather than linking somewhere that 404s.
const router = useRouter()
const linkedModuleItem = computed(() => findModuleByDoctype(props.field.options))
const linkedRoute = computed(() => (props.modelValue && linkedModuleItem.value ? linkedModuleItem.value.route : null))

function openLinkedRecord() {
  if (!linkedRoute.value) return
  router.push({ name: 'DoctypeForm', params: { doctypeRoute: linkedRoute.value, name: props.modelValue } })
}

// --- Quick create ------------------------------------------------------
// A lightweight version of DoctypeForm.vue's own new-record form, scoped to
// just the linked doctype's required fields (Frappe desk's Quick Entry
// dialog does the same - not the doctype's full form, since the whole
// point is staying inside the flow of filling out *this* field). Reuses
// DynamicField so every fieldtype (Select, Date, another Link, ...) still
// renders and behaves exactly like it would on a full form.
const showCreateDialog = ref(false)
const newRecordValues = reactive({})
const newRecordName = ref('')
const creating = ref(false)
const createError = ref(null)

const isPromptNamed = computed(() => metaResource.data?.autoname === 'prompt')

const createFields = computed(() => {
  const metaFields = metaResource.data?.fields || []
  const SKIP_FIELDTYPES = new Set(['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Heading', 'Button'])
  return metaFields.filter((f) => f.reqd && !SKIP_FIELDTYPES.has(f.fieldtype) && f.fieldtype !== 'Table')
})

function openCreateDialog() {
  for (const key of Object.keys(newRecordValues)) delete newRecordValues[key]
  newRecordName.value = ''
  createError.value = null
  showCreateDialog.value = true
}

async function submitNewRecord() {
  if (isPromptNamed.value && !newRecordName.value.trim()) {
    createError.value = 'Name is required.'
    return
  }
  creating.value = true
  createError.value = null
  try {
    const doc = { doctype: props.field.options, ...newRecordValues }
    if (isPromptNamed.value) doc.name = newRecordName.value.trim()
    const created = await call('frappe.client.insert', { doc })
    toast.success(`${props.field.options} created`)
    showCreateDialog.value = false
    recordsResource.fetch()
    // String(...) for the same reason as options above - an autoincrement
    // doctype's created.name comes back as a JSON number.
    emit('update:modelValue', String(created.name))
  } catch (e) {
    createError.value = e
  } finally {
    creating.value = false
  }
}
</script>
