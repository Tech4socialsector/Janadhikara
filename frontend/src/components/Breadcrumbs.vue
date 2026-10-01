<template>
  <!-- Helpdesk-style header trail (frappe-ui Breadcrumbs): every crumb medium
  weight, ancestors in muted gray that darken on hover, the current page in
  strong gray, and a light "/" between them. 14px - one step under
  Helpdesk's own 16px, to keep the header compact. -->
  <nav v-if="crumbs.length > 1" class="flex min-w-0 items-center text-base font-medium">
    <template v-for="(crumb, idx) in crumbs" :key="idx">
      <span v-if="idx > 0" class="mx-1 flex-shrink-0 text-sm text-ink-gray-4" aria-hidden="true">/</span>
      <router-link
        v-if="crumb.to && idx < crumbs.length - 1"
        :to="crumb.to"
        class="flex-shrink-0 truncate rounded px-0.5 py-1 text-ink-gray-5 hover:text-ink-gray-7"
      >
        {{ crumb.label }}
      </router-link>
      <span v-else class="truncate px-0.5 py-1 text-ink-gray-9">
        {{ crumb.label }}
      </span>
    </template>
  </nav>
  <h1 v-else class="truncate text-base font-medium text-ink-gray-9">
    {{ pageTitle }}
  </h1>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { pageTitle } from '@/data/pageTitle'
import { findModuleByRoute } from '@/data/modules'
import { findSettingsEntryByRoute } from '@/data/settingsEntries'

// Rebuilt from the current route + module metadata rather than pages
// pushing their own crumb list - every doctype list/form page already goes
// through the same generic DoctypeList/DoctypeNew/DoctypeForm route names
// (see router.js), so the trail (module -> doctype list -> record) can be
// derived once, here, instead of every page repeating "here's my own
// breadcrumb" wiring. Falls back to the flat page title alone (the
// previous, pre-breadcrumb behavior) for the one-level pages - Home,
// Worklist, Dashboard, etc. - where a trail would just be noise.
const route = useRoute()

const crumbs = computed(() => {
  const doctypeRoute = route.params.doctypeRoute
  if (!doctypeRoute) return []

  const moduleItem = findModuleByRoute(doctypeRoute)
  const listLabel = moduleItem?.label || findSettingsEntryByRoute(doctypeRoute)?.label || doctypeRoute
  const list = [{ label: 'Home', to: { name: 'Home' } }]
  // There's no dedicated page per module (Home just lists every module's
  // tiles inline), so the module crumb links back to Home too rather than
  // to a route that doesn't exist.
  if (moduleItem?.module?.label) {
    list.push({ label: moduleItem.module.label, to: { name: 'Home' } })
  }
  list.push({ label: listLabel, to: { name: 'DoctypeList', params: { doctypeRoute } } })

  if (route.name === 'DoctypeNew') {
    list.push({ label: `New ${listLabel}` })
  } else if (route.name === 'DoctypeForm') {
    // pageTitle is kept in sync with the record's own title_field value by
    // DoctypeForm.vue (falling back to its id) - reused here rather than
    // route.params.name directly, which is always the raw id regardless of
    // whether the doctype has a title_field a user would actually
    // recognize the record by.
    list.push({ label: pageTitle.value || route.params.name })
  }
  return list
})
</script>
