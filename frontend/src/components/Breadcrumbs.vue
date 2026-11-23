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
        class="inline-flex flex-shrink-0 items-center rounded px-0.5 py-1 text-ink-gray-5 hover:text-ink-gray-7"
      >
        <LucideIcon v-if="crumb.home" name="house" class="relative -top-px mr-1 h-4 w-4 flex-shrink-0" />
        <span class="truncate">{{ crumb.label }}</span>
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
import LucideIcon from '@/components/LucideIcon.vue'
import { useRoute } from 'vue-router'
import { pageTitle } from '@/data/pageTitle'
import { t } from '@/utils/translate'
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
  const home = { label: t('Home'), to: { name: 'Home' }, home: true }
  // The app's own pages: Home / <page>
  if (route.name === 'Dashboard') return [home, { label: t('Dashboard') }]
  if (route.name === 'Worklist') return [home, { label: t('Worklist') }]
  if (route.name === 'Help') return [home, { label: t('Help') }]
  if (route.name === 'SyncData') return [home, { label: t('Sync Data') }]
  if (route.name === 'OfflineEdit' || route.name === 'OfflineRecord') return [home, { label: t('Sync Data'), to: { name: 'SyncData' } }, { label: pageTitle.value || t('Record') }]
  // The support desk: Home / Support, then a new ticket or the ticket itself
  if (route.name === 'SupportDesk') return [home, { label: t('Support') }]
  if (route.name === 'SupportNew') return [home, { label: t('Support'), to: { name: 'SupportDesk' } }, { label: t('New ticket') }]
  if (route.name === 'SupportTicket') return [home, { label: t('Support'), to: { name: 'SupportDesk' } }, { label: pageTitle.value || route.params.name }]

  const doctypeRoute = route.params.doctypeRoute
  if (!doctypeRoute) return []

  if (doctypeRoute === 'todo') {
    return [
      home,
      { label: t('Worklist'), to: { name: 'Worklist' } },
      { label: route.name === 'DoctypeNew' ? 'New task' : pageTitle.value || 'Task' },
    ]
  }

  const moduleItem = findModuleByRoute(doctypeRoute)
  const listLabel = t(moduleItem?.label || findSettingsEntryByRoute(doctypeRoute)?.label || doctypeRoute)
  const list = [home]
  // There's no dedicated page per group (Home lists every group as a card), so the group crumb opens Home
  // scrolled to that group's card.
  if (moduleItem?.module?.label) {
    list.push({ label: t(moduleItem.module.label), to: { name: 'Home', query: { group: moduleItem.module.name || moduleItem.module.label } } })
  }
  list.push({ label: listLabel, to: { name: 'DoctypeList', params: { doctypeRoute } } })

  if (route.name === 'DoctypeNew') {
    list.push({ label: `${t('New')} ${listLabel}` })
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
