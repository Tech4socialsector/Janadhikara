<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <div class="flex items-center gap-2">
          <Button variant="ghost" @click="goBack">
            <template #prefix>
              <FeatherIcon name="arrow-left" class="h-4 w-4" />
            </template>
            Back
          </Button>
          <span
            v-if="isDirty"
            class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
          >
            Not Saved
          </span>
        </div>
      </template>
      <template #actions>
        <Button
          v-if="!isNew && !loadError && canDelete"
          variant="subtle"
          theme="red"
          :loading="deleting"
          @click="showDeleteConfirm = true"
        >
          Delete
        </Button>
        <Button v-if="!loadError" variant="solid" :loading="saving" @click="save">
          Save
        </Button>
      </template>
    </PageHeader>

    <Dialog v-model="showDeleteConfirm" :options="{ title: 'Delete this record?', size: 'sm' }">
      <template #body-content>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          This permanently deletes {{ name }}. This cannot be undone.
        </p>
        <ErrorMessage class="mt-3" :message="deleteError" />
        <div class="mt-4 flex justify-end gap-2">
          <Button @click="showDeleteConfirm = false">Cancel</Button>
          <Button variant="solid" theme="red" :loading="deleting" @click="confirmDelete">Delete</Button>
        </div>
      </template>
    </Dialog>

    <div v-if="metaResource.loading && !metaResource.data" class="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
      <div v-for="i in 6" :key="i" class="space-y-1.5">
        <Skeleton width="30%" height="0.75rem" />
        <Skeleton height="2.25rem" />
      </div>
    </div>
    <ErrorMessage v-else-if="loadError" :message="loadError" />

    <div v-else-if="!isNew && existingDoc.loading && !existingDoc.doc" class="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
      <div v-for="i in 6" :key="i" class="space-y-1.5">
        <Skeleton width="30%" height="0.75rem" />
        <Skeleton height="2.25rem" />
      </div>
    </div>

    <form v-else @submit.prevent="save">
      <!-- Doctypes with more than one Tab Break (useFormTabs) get an actual
      tab switcher instead of every field flattening into one long scroll -
      the common case (no tabs, or just the implicit first one) skips this
      nav entirely and renders exactly as before. Desktop-only (sm:flex,
      hidden by default): mobile gets an accordion instead, right below,
      since a horizontal tab bar squeezed onto a phone-width screen either
      wraps awkwardly or needs its own scroll - a stacked list of
      expand/collapse sections is the same pattern Frappe desk's own
      mobile view uses instead of tabs at that width. -->
      <div v-if="tabs.length > 1" class="mb-4 hidden gap-1 border-b sm:flex dark:border-gray-800">
        <button
          v-for="(tab, idx) in tabs"
          v-show="isTabVisible(tab)"
          :key="idx"
          type="button"
          class="border-b-2 px-3 py-2 text-sm font-medium"
          :class="idx === activeTabIdx
            ? 'border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100'
            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'"
          @click="activeTabIdx = idx"
        >
          {{ tab.label || 'Details' }}
        </button>
      </div>

      <!-- Renders in the doctype's own field_order, the same way Frappe
      desk does: each Section Break starts a fresh block of 1-2 columns
      (however many Column Breaks it declares), and fields fill down each
      column top-to-bottom in declaration order - not the previous
      CSS-multi-column reflow, which packed fields by height and lost the
      doctype's actual left/right placement. A field that's "wide"
      elsewhere in Desk (Small Text, Geolocation, etc.) still just renders
      at its own column's width here, matching Frappe desk itself - it does
      not span into a neighboring column. Every FormControl-based field is
      a fixed h-8 (see DynamicField.vue) so fields line up evenly whichever
      column they land in. Hidden on mobile when there's more than one
      tab - the accordion below covers that case there instead; with only
      one (implicit or real) tab, there's nothing an accordion would add
      over this, so it stays the only rendering at every width. -->
      <FormTabSections
        v-if="tabs.length <= 1"
        :sections="activeTabSections"
        :doctype="doctype"
        :name="name"
        :is-new="isNew"
        v-model:new-doc-name="newDocName"
        :values="values"
        :show-name-field="isPromptNamed"
        @address-resolved="onAddressResolved"
        @pincode-resolved="onPincodeResolved"
        @location-resolved="onLocationResolved"
      />
      <FormTabSections
        v-else
        class="hidden sm:block"
        :sections="activeTabSections"
        :doctype="doctype"
        :name="name"
        :is-new="isNew"
        v-model:new-doc-name="newDocName"
        :values="values"
        :show-name-field="activeTabIdx === 0 && isPromptNamed"
        @address-resolved="onAddressResolved"
        @pincode-resolved="onPincodeResolved"
        @location-resolved="onLocationResolved"
      />

      <!-- Mobile accordion (sm:hidden): every tab renders as its own
      collapsible header instead of only the active one - collapsed by
      default except the first, expanded/collapsed independently of the
      desktop activeTabIdx (a phone-width user isn't constrained to
      viewing one tab at a time the way the desktop switcher is). -->
      <div v-if="tabs.length > 1" class="space-y-3 sm:hidden">
        <div
          v-for="(tab, idx) in tabs"
          v-show="isTabVisible(tab)"
          :key="idx"
          class="rounded-lg border dark:border-gray-800"
        >
          <button
            type="button"
            class="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-gray-900 dark:text-gray-100"
            @click="expandedMobileTabs[idx] = !expandedMobileTabs[idx]"
          >
            {{ tab.label || 'Details' }}
            <FeatherIcon
              :name="expandedMobileTabs[idx] ? 'chevron-up' : 'chevron-down'"
              class="h-4 w-4 flex-shrink-0 text-gray-400"
            />
          </button>
          <div v-if="expandedMobileTabs[idx]" class="border-t px-4 py-4 dark:border-gray-800">
            <FormTabSections
              :sections="tab.sections"
              :doctype="doctype"
              :name="name"
              :is-new="isNew"
              v-model:new-doc-name="newDocName"
              :values="values"
              :show-name-field="idx === 0 && isPromptNamed"
              @address-resolved="onAddressResolved"
              @pincode-resolved="onPincodeResolved"
              @location-resolved="onLocationResolved"
            />
          </div>
        </div>
      </div>

      <div v-if="tableFields.length" class="mt-6 space-y-6">
        <ChildTable
          v-for="field in tableFields"
          :key="field.fieldname"
          :field="field"
          v-model="values[field.fieldname]"
        />
      </div>

      <ErrorMessage class="mt-4" :message="saveError" />

      <ConnectionsPanel
        v-if="!isNew && metaResource.data?.links?.length"
        :doctype="doctype"
        :name="name"
        :links="metaResource.data.links"
      />
    </form>
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onKeyStroke } from '@vueuse/core'
import { useDoc, useNewDoc, useCall, call, Button, Dialog, ErrorMessage, FeatherIcon, toast } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import Skeleton from '@/components/Skeleton.vue'
import ChildTable from '@/components/ChildTable.vue'
import FormTabSections from '@/components/FormTabSections.vue'
import ConnectionsPanel from '@/components/ConnectionsPanel.vue'
import { useMeta, useFormFields, useFormTabs, useTableFields } from '@/data/useMeta'
import { getDoctypeHooks } from '@/doctype-hooks'
import { setPageTitle } from '@/data/pageTitle'
import { useCommonFieldDefaults } from '@/composables/useCommonFieldDefaults'
import { useFetchFromFields } from '@/composables/useFetchFromFields'
import { usePincodeLookup } from '@/composables/usePincodeLookup'
import { getValidatorForField } from '@/utils/validation'
import { evaluateDependsOn } from '@/utils/dependsOn'

const { doctype, isNew, name } = defineProps({
  doctype: { type: String, required: true },
  isNew: { type: Boolean, default: false },
  name: { type: String, default: null },
})

const route = useRoute()
const router = useRouter()

// Mirrors DoctypeList.vue's routing: generic /:doctypeRoute doctypes use the
// shared DoctypeList route name, dedicated doctypes (e.g. Email Account)
// have their own List route name derived the same way.
const isGenericRoute = route.name === 'DoctypeNew' || route.name === 'DoctypeForm'

function goBack() {
  if (isGenericRoute) {
    router.push({ name: 'DoctypeList', params: { doctypeRoute: route.params.doctypeRoute } })
  } else {
    router.push({ name: route.name.replace('New', 'List').replace('Form', 'List') })
  }
}

const metaResource = useMeta(doctype)
const fields = useFormFields(metaResource)
const tabs = useFormTabs(metaResource)
const tableFields = useTableFields(metaResource)
const hooks = getDoctypeHooks(doctype)
const { applyFetchFrom } = useFetchFromFields({ metaResource })
const { lookupPincode } = usePincodeLookup()

// Only the active tab's sections render, but `fields` (every field, flat)
// stays the source for the hook-diffing/snapshot logic below it - a field
// on a tab that isn't currently showing can still be changed by a hook
// (e.g. a default set onLoad) and that must still be picked up.
const activeTabIdx = ref(0)
watch(tabs, () => { activeTabIdx.value = 0 })
const activeTabSections = computed(
  () => tabs.value[activeTabIdx.value]?.sections || [{ label: null, columns: [fields.value] }],
)

// Mobile accordion's own open/closed state per tab (see template) - kept
// separate from activeTabIdx since a phone-width user can have any
// number of these open/closed independently, not just one "active" tab
// the way the desktop switcher works. Starts with only the first
// expanded, same as Frappe desk's own mobile form view; reset alongside
// activeTabIdx whenever tabs themselves change (a different doctype/
// record loading fresh metadata).
const expandedMobileTabs = ref({ 0: true })
watch(tabs, () => { expandedMobileTabs.value = { 0: true } })

// "Prompt" autoname doctypes (simple master/lookup tables like Village) have
// no field backing their name at all - Frappe desk handles this with a
// "Set Name" popup on create. This generic form has no such popup, so
// without this the record's name is never collected or shown anywhere.
const isPromptNamed = computed(() => metaResource.data?.autoname === 'prompt')
const newDocName = ref('')

const newDoc = isNew ? useNewDoc(doctype) : null
const existingDoc = isNew ? null : useDoc({ doctype, name })

// existingDoc.error used to be silently ignored - a failed record fetch
// (permission denied, the record renamed/deleted since the link that led
// here was created, etc.) fell through to the `v-else` form branch and
// rendered a blank, fieldless form with no explanation and a Save button
// that would only fail again once clicked, instead of a clear error.
const loadError = computed(() => metaResource.error || existingDoc?.error)

// Delete was entirely missing from this app's generic form - useDoc()
// already exposes a ready DELETE call, it just wasn't wired to anything.
// Gated on the same frappe.client.has_permission check LinkField.vue uses
// for its own "+ Create New X" option, so a user without delete rights on
// this doctype never sees a button that would only 403 when clicked.
const deletePermissionResource = isNew
  ? null
  : useCall({
      url: '/api/v2/method/frappe.client.has_permission',
      method: 'GET',
      params: () => ({ doctype, docname: name, perm_type: 'delete' }),
      immediate: false,
      transform: (data) => data?.has_permission,
    })
if (deletePermissionResource) deletePermissionResource.fetch()
const canDelete = computed(() => !!deletePermissionResource?.data)

const showDeleteConfirm = ref(false)
const deleting = ref(false)
const deleteError = ref(null)

async function confirmDelete() {
  deleting.value = true
  deleteError.value = null
  try {
    await existingDoc.delete.submit()
    toast.success('Deleted')
    showDeleteConfirm.value = false
    goBack()
  } catch (e) {
    deleteError.value = e
  } finally {
    deleting.value = false
  }
}

// `values` is the single source of truth the form binds to - a plain
// reactive object kept in sync with newDoc.doc / existingDoc.doc below,
// rather than binding the form directly to either, so both code paths
// (new vs. existing) look identical to DynamicField/ChildTable and to the
// doctype-hooks diffing below.
const values = reactive({})

// Same depends_on convention as DynamicField.vue's fields and
// FormTabSections.vue's sections, applied to a Tab Break itself - a tab
// with no condition always shows.
function isTabVisible(tab) {
  return evaluateDependsOn(tab.dependsOn, values)
}

// The doctype's own title_field (e.g. Household profile's
// household_head_name) is what a record is actually recognized by, same
// as a Link field's own dropdown option already shows (see LinkField.vue)
// - falls back to the record's id when title_field isn't set, or is set
// but genuinely empty on this particular record (a name-only doctype, or
// a title field nobody's filled in yet).
//
// One extra step Frappe's own get_title() doesn't bother with: when
// title_field is itself a Link (Household profile's is - a Link to
// Family members), its raw stored value is just that record's own id
// (e.g. "FM-00003"), not anything a person recognizes - the exact same
// gap LinkField.vue's own display already solves for picking a value,
// just not for showing one that's already picked. The two resources
// below resolve that one level: fetch the linked doctype's own meta (to
// know ITS title_field), then fetch that one record with just its name +
// title_field - not resolved any deeper than that, matching how far
// Frappe desk itself ever goes for this.
const titleFieldDef = computed(() =>
  metaResource.data?.fields?.find((f) => f.fieldname === metaResource.data?.title_field),
)
const linkedDoctype = computed(() =>
  titleFieldDef.value?.fieldtype === 'Link' ? titleFieldDef.value.options : null,
)
const linkedMetaResource = useCall({
  url: computed(() => `/api/v2/doctype/${linkedDoctype.value}/meta`),
  method: 'GET',
  // No cacheKey here (unlike LinkField.vue's identical fetch) - useCall's
  // cacheKey must be a plain string/array, not a computed ref, and unlike
  // LinkField.vue (whose field.options is fixed for that component
  // instance's whole life) linkedDoctype only becomes known once
  // metaResource resolves asynchronously - a computed passed as cacheKey
  // gets spread as if it were an array internally and throws ("e is not
  // iterable"). Skipping the cache namespace just means this one lookup
  // doesn't share frappe-ui's cross-component cache; correctness doesn't
  // depend on it.
  immediate: false,
})
watch(linkedDoctype, (dt) => { if (dt) linkedMetaResource.fetch() })
const linkedTitleFieldName = computed(() => linkedMetaResource.data?.title_field || 'name')

const linkedRecordId = computed(() => values[metaResource.data?.title_field])
const linkedTitleResource = useCall({
  url: computed(() => `/api/v2/document/${linkedDoctype.value}/${linkedRecordId.value}`),
  method: 'GET',
  params: () => ({ fields: JSON.stringify(['name', linkedTitleFieldName.value]) }),
  immediate: false,
})
watch(
  () => [linkedDoctype.value, linkedRecordId.value, linkedTitleFieldName.value],
  () => {
    if (linkedDoctype.value && linkedRecordId.value) linkedTitleResource.fetch()
  },
)

const recordTitle = computed(() => {
  const rawValue = linkedRecordId.value
  if (!rawValue) return name
  if (linkedDoctype.value) {
    return linkedTitleResource.data?.[linkedTitleFieldName.value] || rawValue
  }
  return rawValue
})

watchEffect(() => {
  setPageTitle(isNew ? `New ${metaResource.data?.name || doctype}` : recordTitle.value)
})

function scalarSnapshot() {
  const snap = {}
  for (const f of fields.value) snap[f.fieldname] = values[f.fieldname]
  return snap
}

function childRowsSnapshot() {
  const snap = {}
  for (const f of tableFields.value) {
    snap[f.fieldname] = (values[f.fieldname] || []).map((row) => ({ ...row }))
  }
  return snap
}

function hookCtx() {
  return { isNew, call }
}

// --- Hook wiring state -----------------------------------------------
// doctype-hooks reimplements frappe.ui.form.on(...) client scripts, which
// don't exist in this Vue app. There's no field-level @change event to hook
// into generically (DynamicField/ChildTable are metadata-driven, not aware
// of business logic) - so instead this diffs `values` against its last-seen
// snapshot on every reactive tick, and calls the matching hook for whatever
// changed. A fixed-point loop re-diffs after each hook call (up to 20
// iterations) so a hook-triggered change (e.g. setting date_of_birth) can
// itself cascade into another hook (age, in turn, from date_of_birth).
let lastScalarSnapshot = null
let lastChildSnapshot = null
let applyingHookChange = false

function initSnapshots() {
  lastScalarSnapshot = scalarSnapshot()
  lastChildSnapshot = childRowsSnapshot()
  lastFetchFromSnapshot = scalarSnapshot()
  lastPincodeSnapshot = values.pincode
}

function runScalarDiffLoop() {
  if (!hooks?.onFieldChange || applyingHookChange) return
  applyingHookChange = true
  try {
    for (let i = 0; i < 20; i++) {
      const current = scalarSnapshot()
      const changedField = Object.keys(current).find((k) => current[k] !== lastScalarSnapshot[k])
      if (!changedField) break
      lastScalarSnapshot = current
      hooks.onFieldChange(changedField, values, hookCtx())
    }
    lastScalarSnapshot = scalarSnapshot()
  } finally {
    applyingHookChange = false
  }
}

// fetch_from runs independently of the (synchronous, doctype-hook-gated)
// diff loop above - it applies to every doctype regardless of whether one
// has custom hooks, and the lookup itself is a server round trip, which
// doesn't fit that loop's synchronous fixed-point re-diffing.
let lastFetchFromSnapshot = null
async function runFetchFromDiff() {
  if (applyingHookChange) return
  const current = scalarSnapshot()
  if (!lastFetchFromSnapshot) {
    lastFetchFromSnapshot = current
    return
  }
  const changedField = Object.keys(current).find((k) => current[k] !== lastFetchFromSnapshot[k])
  lastFetchFromSnapshot = current
  if (changedField) await applyFetchFrom(changedField, values)
}

// A field opts into one of these geo-derived roles by declaring the
// matching marker as its own `options` value - the same convention
// IndiaGeoField's india_state/india_district uses (see DynamicField.vue),
// rather than this page hardcoding specific fieldnames like "pincode" or
// "address". Any doctype can wire up any of its own Data/Float fields
// this way just by setting `options` in the DocType editor, portable to
// real Desk too (a plain, unused DocField property there).
const GEO_ROLE_OPTIONS = {
  pincode: 'geo_pincode',
  // state/district reuse IndiaGeoField's own control-type markers (see
  // DynamicField.vue) rather than a separate geo_state/geo_district pair
  // - a field opting into the India state/district dropdown control IS
  // the thing a pincode lookup should resolve into; there's no case in
  // this app where those would need to be two different fields.
  state: 'india_state',
  district: 'india_district',
  address: 'geo_address',
  latitude: 'geo_latitude',
  longitude: 'geo_longitude',
}
function fieldWithGeoRole(role) {
  return fields.value.find((f) => f.options === GEO_ROLE_OPTIONS[role])
}

// Auto-fills the geo_state/geo_district fields from geo_pincode (see
// usePincodeLookup.js) - same independent-of-hooks reasoning as
// fetch_from above (a server round trip doesn't fit the synchronous diff
// loop), and only runs at all when the doctype actually declares all
// three roles, so this stays a no-op cost for every doctype that doesn't.
const pincodeField = computed(() => fieldWithGeoRole('pincode'))
const hasPincodeFields = computed(() =>
  !!pincodeField.value && !!fieldWithGeoRole('state') && !!fieldWithGeoRole('district'),
)
let lastPincodeSnapshot = null
async function runPincodeLookupDiff() {
  if (applyingHookChange || !hasPincodeFields.value) return
  const current = values[pincodeField.value.fieldname]
  if (lastPincodeSnapshot === null) {
    lastPincodeSnapshot = current
    return
  }
  if (current === lastPincodeSnapshot) return
  lastPincodeSnapshot = current
  const result = await lookupPincode(current)
  if (result) {
    values[fieldWithGeoRole('state').fieldname] = result.state
    values[fieldWithGeoRole('district').fieldname] = result.district
  }
}

function runChildDiff() {
  if (!hooks?.onChildFieldChange || applyingHookChange) return
  const current = childRowsSnapshot()
  for (const tableField of tableFields.value) {
    const fieldname = tableField.fieldname
    const currentRows = current[fieldname] || []
    const lastRows = lastChildSnapshot[fieldname] || []
    currentRows.forEach((row, idx) => {
      const lastRow = lastRows[idx]
      if (!lastRow) return
      const changedKey = Object.keys(row).find((k) => row[k] !== lastRow[k])
      if (changedKey) {
        hooks.onChildFieldChange(fieldname, changedKey, row, values)
      }
    })
  }
  lastChildSnapshot = current
}

watch(
  () => [scalarSnapshot(), childRowsSnapshot()],
  () => {
    if (applyingHookChange || !lastScalarSnapshot) return
    runScalarDiffLoop()
    runChildDiff()
    runFetchFromDiff()
    runPincodeLookupDiff()
  },
  { deep: true },
)

// --- Unsaved-changes indicator ----------------------------------------
// Same convention as Frappe desk's own form: a "Not Saved" badge next to
// the title once the form differs from what's actually on the server (or,
// for a new record, from wherever it started - its own onLoad hook/
// common defaults/query-string prefill, none of which count as the user
// having changed anything). `cleanSnapshot` is a plain JSON string of
// `values` at the last point the form was known to match the server;
// isDirty just compares the live JSON against it on every reactive tick
// rather than diffing field-by-field.
// Plain `ref`s, not plain variables - a computed only re-evaluates when
// something it actually read on its LAST run changes, and only reactive
// state (refs/reactive properties) counts as something it "read". An
// earlier version of this used plain `let`s for cleanSnapshot/
// suppressDirtyTracking: on the very first evaluation, cleanSnapshot was
// still null, so the early-return fired before ever reaching
// `JSON.stringify(values)` below it - meaning `values` was never
// registered as a dependency at all, and no later edit could ever
// trigger a re-evaluation again for the lifetime of the component.
const cleanSnapshot = ref(null)
const suppressDirtyTracking = ref(false)

function markClean() {
  cleanSnapshot.value = JSON.stringify(values)
  suppressDirtyTracking.value = false
}

const isDirty = computed(() => {
  if (suppressDirtyTracking.value || cleanSnapshot.value === null) return false
  return JSON.stringify(values) !== cleanSnapshot.value
})

// Same as desk's own "leave site?" browser prompt for an unsaved form -
// only wired for a hard navigation away (closing the tab, typing a new
// URL, refreshing), since that's the one kind of "leaving" this generic
// form can't otherwise offer an in-app confirmation for. In-app
// navigation (Back button, sidebar, breadcrumbs) is a bigger, separate
// piece of work (a router guard + confirmation dialog) that wasn't asked
// for here - this covers the same "don't lose typed work by accident"
// concern for the case that's cheapest to get right.
function confirmLeaveIfDirty(e) {
  if (!isDirty.value) return
  e.preventDefault()
}
onMounted(() => window.addEventListener('beforeunload', confirmLeaveIfDirty))
onBeforeUnmount(() => window.removeEventListener('beforeunload', confirmLeaveIfDirty))

const { applyCommonFieldDefaults } = useCommonFieldDefaults({
  doctype,
  fields,
  values,
  isNew,
  onApplied: markClean,
})

// A Geolocation field's reverse-geocoded address (see GeoLocationField.vue)
// has nowhere of its own to live - it's meant for whichever field on the
// same form declares the matching geo_* role (see GEO_ROLE_OPTIONS
// above), the same options-as-marker convention as IndiaGeoField's
// india_state/india_district, rather than this page hardcoding specific
// fieldnames like "address"/"pincode"/"latitude"/"longitude".
function onAddressResolved(addressText) {
  const field = fieldWithGeoRole('address')
  if (field) values[field.fieldname] = addressText
}

// Same convention as onAddressResolved above. Setting it here also feeds
// runPincodeLookupDiff below the normal way (it just watches the
// geo_pincode field for changes), so a location captured on the map
// cascades into State/District auto-filling too, the same as if the user
// had typed the pincode in directly.
function onPincodeResolved(pincode) {
  const field = fieldWithGeoRole('pincode')
  if (field) values[field.fieldname] = pincode
}

// Same convention again, for whichever fields declare the geo_latitude/
// geo_longitude roles - the Geolocation field's own value already stores
// the point as GeoJSON, but that's not something a plain Float field
// elsewhere on the form can read on its own, so the raw coordinates are
// mirrored out here too whenever a location is actually captured (click,
// drag, or "use my location"), same as address/pincode.
function onLocationResolved(point) {
  const latField = fieldWithGeoRole('latitude')
  const lngField = fieldWithGeoRole('longitude')
  if (latField) values[latField.fieldname] = point.lat
  if (lngField) values[lngField.fieldname] = point.lng
}

// A "New" link from the Connections panel (see ConnectionsPanel.vue) opens
// this form with the originating record's own id in the query string (e.g.
// ?household_id=HH-00001), so creating the new record doesn't require
// re-picking a Link the user already had open on screen. Only applied to
// a real field on this doctype - a query param that doesn't match one is
// silently ignored rather than polluting `values` with an untracked key.
//
// Called from two places: once from the doc-load watcher below (covers
// the common case where metaResource has already resolved by then), and
// again from its own watch on `fields` (covers a new record, where
// newDoc.doc starts as a synchronously-available empty reactive object -
// that watcher's first, immediate firing runs before metaResource/fields
// has loaded from the server at all, so `fields.value` is still `[]` and
// every query param looks like "not a real field" at that point).
function applyQueryPrefill() {
  if (!isNew) return
  for (const [key, value] of Object.entries(route.query)) {
    if (fields.value.some((f) => f.fieldname === key) && !values[key]) {
      values[key] = value
    }
  }
}
watch(fields, applyQueryPrefill)

// A brand-new record's own doc starts as a bare {} (see useNewDoc.ts) - it
// has no key at all for a Table field until something adds a row, so the
// Object.keys(doc) loop below never sets values[a Table fieldname] for a
// new record. ChildTable.vue's own `default: () => []` prop only supplies
// a fallback for *rendering*, never for what its v-model actually writes
// back to - addRow() there pushes into that throwaway default array, not
// into values[fieldname] (still undefined), so a newly-added row looked
// present in the grid (Vue re-rendered off the local mutation) but Save's
// payload never contained it at all (confirmed live: "No rows yet" after
// Done, even though every field in the row editor was filled correctly
// and the row visibly appeared to have been added). Explicitly seeding
// every Table field to a real array up front, the same way
// Object.keys(doc) already seeds every other field this doc happens to
// have, closes that gap.
//
// Same two-call-site reasoning as applyQueryPrefill just above (and same
// reason it's not simply the doc-load watcher alone): tableFields depends
// on metaResource.data, which - like `fields` - hasn't necessarily
// resolved by the doc-load watcher's own immediate first firing.
// !== undefined (not falsy) guards against re-running this once
// metaResource resolves and clobbering a row a user already added in that
// window - only a field this doc has genuinely never touched gets seeded.
function initEmptyTableFields() {
  if (!isNew) return
  for (const tableField of tableFields.value) {
    if (values[tableField.fieldname] === undefined) {
      values[tableField.fieldname] = []
    }
  }
}
watch(tableFields, initEmptyTableFields)

// --- Load doc into `values` -------------------------------------------
watch(
  () => (isNew ? newDoc?.doc : existingDoc?.doc),
  (doc) => {
    if (!doc) return
    suppressDirtyTracking.value = true
    Object.keys(doc).forEach((k) => {
      values[k] = doc[k]
    })
    initEmptyTableFields()
    initSnapshots()
    if (isNew && hooks?.onLoad) {
      applyingHookChange = true
      hooks.onLoad(values, hookCtx())
      applyingHookChange = false
      initSnapshots()
    }
    applyCommonFieldDefaults()
    applyQueryPrefill()
    // nextTick, not immediately: onLoad/common-defaults/query-prefill above
    // are all synchronous, but useCommonFieldDefaults also re-applies later
    // on its own (via a watch on `fields` and on each rule's own resource -
    // see useCommonFieldDefaults.js), independent of this watcher, whenever
    // one of those resolves after this point. markClean() gets called again
    // from applyCommonFieldDefaults itself for that reason (see below); this
    // call just covers the common, synchronous case (an existing record's
    // fields loading, or a new record's onLoad hook) without waiting on
    // anything async.
    nextTick(markClean)
  },
  { immediate: true, deep: true },
)

const saving = ref(false)
const saveError = ref(null)

// Same format validators DynamicField.vue shows inline (see
// utils/validation.js) - re-checked here so a bad value can't slip through
// on save via Ctrl+S or a pasted value the user never actually blurred
// out of (inline display alone only catches a field once it's been
// touched).
function firstValidationError() {
  for (const field of fields.value) {
    const validator = getValidatorForField(field)
    if (!validator) continue
    const error = validator(values[field.fieldname])
    if (error) return `${field.label}: ${error}`
  }
  return null
}

async function save() {
  if (isNew && isPromptNamed.value && !newDocName.value.trim()) {
    saveError.value = 'Name is required.'
    return
  }
  const validationError = firstValidationError()
  if (validationError) {
    saveError.value = validationError
    return
  }
  saving.value = true
  saveError.value = null
  try {
    if (isNew) {
      Object.assign(newDoc.doc, values)
      if (isPromptNamed.value) newDoc.doc.name = newDocName.value.trim()
      const created = await newDoc.submit()
      // useCall's submit() resolves even when the server rejects the
      // request (a 4xx/5xx doesn't make the underlying fetch throw) - it
      // only ever populates the resource's own `.error`, so a MandatoryError
      // or any other server-side validation failure would otherwise fall
      // straight through to the success toast and redirect below with the
      // record never actually having been created. Checking `.error`
      // explicitly is the only reliable way to know the save actually
      // failed.
      if (newDoc.error) throw newDoc.error
      toast.success('Created')
      if (isGenericRoute) {
        router.replace({
          name: 'DoctypeForm',
          params: { doctypeRoute: route.params.doctypeRoute, name: created.name },
        })
      } else {
        router.replace({ name: route.name.replace('New', 'Form'), params: { name: created.name } })
      }
    } else {
      await existingDoc.setValue.submit(values)
      // Same reasoning as newDoc.error above - setValue.submit() resolving
      // doesn't mean the save actually succeeded server-side.
      if (existingDoc.setValue.error) throw existingDoc.setValue.error
      toast.success('Saved')
      markClean()
    }
  } catch (e) {
    saveError.value = e
  } finally {
    saving.value = false
  }
}

onKeyStroke((e) => (e.key === 's' || e.key === 'S') && (e.metaKey || e.ctrlKey), (e) => {
  e.preventDefault()
  if (!saving.value) save()
})
</script>
