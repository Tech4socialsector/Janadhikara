<template>
  <!-- Like Frappe desk's Connections: one small card per linked document, up to four in a row. Its name opens the
  list of those records (filtered to this one), the count shows how many there are, and + starts a new one. -->
  <div v-if="connections.length" class="mb-5 border-b pb-4 dark:border-gray-800">
    <h3 class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Connections') }}</h3>
    <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <div
        v-for="conn in connections"
        :key="conn.key"
        class="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 dark:border-gray-800"
      >
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center gap-2 text-left text-sm text-gray-800 hover:text-gray-950 dark:text-gray-200 dark:hover:text-white"
          :disabled="!conn.route"
          @click="openList(conn)"
        >
          <span class="truncate">{{ t(conn.label) }}</span>
          <span
            v-if="conn.countResource.data != null"
            class="flex h-5 min-w-5 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 px-1.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400"
          >
            {{ conn.countResource.data }}
          </span>
        </button>
        <Button v-if="conn.canCreate" variant="ghost" size="sm" icon="plus" :tooltip="t('Add')" :aria-label="t('Add')" @click="addNew(conn)" />
      </div>
    </div>
    <!-- A household: one place per family member (adults + children). Members already profiled are listed by name;
    for the rest, type the name and Add profile opens their Individual Profile with the household and name filled in. -->
    <div v-if="memberSlots" class="mt-3 rounded-lg border px-3 py-2.5 dark:border-gray-800">
      <p class="mb-2 text-sm text-gray-700 dark:text-gray-300">
        {{ t('Family members') }}: {{ memberSlots.profiles.length }} {{ t('of') }} {{ memberSlots.expected }} {{ t('profiles added') }}
      </p>
      <div class="space-y-1.5">
        <button
          v-for="(p, i) in memberSlots.profiles"
          :key="p.name"
          type="button"
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-gray-800 hover:bg-surface-gray-1 dark:text-gray-200"
          @click="openProfile(p.name)"
        >
          <FeatherIcon name="check-circle" class="h-4 w-4 flex-shrink-0 text-green-600" />
          <span class="truncate">{{ i + 1 }}. {{ p.member_name || p.name }}</span>
        </button>
        <div v-for="i in memberSlots.missing" :key="'new' + i" class="flex items-center gap-2">
          <span class="w-6 flex-shrink-0 text-right text-sm text-gray-500">{{ memberSlots.profiles.length + i }}.</span>
          <input
            v-model="newNames[i]"
            type="text"
            class="min-w-0 flex-1 rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-sm"
            :placeholder="t('Name of the member')"
            :aria-label="t('Name of the member')"
          />
          <Button size="sm" icon-left="plus" @click="addMember(i)">{{ t('Add profile') }}</Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FeatherIcon, Button, useCall } from 'frappe-ui'
import { findModuleByDoctype } from '@/data/modules'
import { t } from '@/utils/translate'

// Frappe desk's own "Connections" tab, driven the same way it is in real
// Desk: a doctype's own `links` metadata (DocType Link child rows) names
// every other doctype that links back to it, and the field on that side
// that holds the connection. Nothing here is hardcoded per-doctype - any
// doctype whose meta declares `links` gets a panel automatically.
//
// `links` is read once at setup time (not wrapped in a computed) because
// each connection owns its own pair of useCall resources - creating those
// dynamically inside a computed's mapper would recreate them on every
// re-evaluation instead of once per connection, which is not how
// composables like useCall are meant to be used (they're meant to be
// called during a component's own setup, not lazily inside a getter).
// This is fine in practice: `links` comes from the parent's already-loaded
// doctype meta and doesn't change after this component mounts.
const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
  links: { type: Array, default: () => [] },
  // the record's own values: a household's member count decides how many member profiles are expected
  values: { type: Object, default: () => ({}) },
})

const router = useRouter()

const connections = props.links
  .filter((l) => !l.hidden)
  .map((l) => {
    const key = `${l.link_doctype}:${l.link_fieldname}`
    const moduleItem = findModuleByDoctype(l.link_doctype)
    const countResource = useCall({
      url: '/api/v2/method/frappe.client.get_count',
      method: 'GET',
      params: () => ({ doctype: l.link_doctype, filters: JSON.stringify({ [l.link_fieldname]: props.name }) }),
      immediate: false,
    })
    return {
      key,
      linkDoctype: l.link_doctype,
      linkFieldname: l.link_fieldname,
      label: moduleItem?.label || l.link_doctype,
      route: moduleItem?.route || null,
      canCreate: !!moduleItem?.route,
      countResource,
    }
  })

// Member profiles of a household (see the template): how many are expected, and those already made.
const memberConn = props.doctype === 'Household Profile' ? connections.find((c) => c.linkDoctype === 'Individual Profile' && c.route) : null
const memberProfiles = useCall({
  url: '/api/v2/document/Individual Profile',
  method: 'GET',
  params: () => ({ fields: JSON.stringify(['name', 'member_name']), filters: JSON.stringify({ household: props.name }), order_by: 'creation asc', limit: 100 }),
  immediate: false,
})
const newNames = reactive({})
const memberSlots = computed(() => {
  const expected = Number(props.values?.member_count) || 0
  if (!memberConn || !expected) return null
  const profiles = memberProfiles.data || []
  return { expected, profiles, missing: Math.max(0, expected - profiles.length) }
})
function addMember(i) {
  router.push({
    name: 'DoctypeNew',
    params: { doctypeRoute: memberConn.route },
    query: { household: props.name, ...(newNames[i]?.trim() ? { member_name: newNames[i].trim() } : {}) },
  })
}
function openProfile(profile) {
  router.push({ name: 'DoctypeForm', params: { doctypeRoute: memberConn.route, name: profile } })
}

// Re-fetch every connection's count whenever the record itself changes
// (e.g. navigating from one Household profile to another without a full
// page reload) - immediate:true covers the first mount.
watch(
  () => props.name,
  () => {
    for (const conn of connections) {
      conn.countResource.fetch()
    }
    if (memberConn) memberProfiles.fetch()
  },
  { immediate: true },
)

function openList(conn) {
  if (!conn.route) return
  router.push({
    name: 'DoctypeList',
    params: { doctypeRoute: conn.route },
    query: { filters: JSON.stringify({ [conn.linkFieldname]: props.name }) },
  })
}

function addNew(conn) {
  if (!conn.route) return
  router.push({
    name: 'DoctypeNew',
    params: { doctypeRoute: conn.route },
    query: { [conn.linkFieldname]: props.name },
  })
}
</script>
