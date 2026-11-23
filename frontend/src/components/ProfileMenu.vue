<template>
  <!-- The signed-in person, at the end of the header: their picture opens a menu - who you are, settings, a way to the
  Desk, refresh, and sign out - like the account menu of other apps. -->
  <Dropdown :options="options" placement="bottom-end">
    <!-- the menu starts with who is signed in: picture, name and email, once -->
    <template #group-label="{ group }">
      <div v-if="group.key === 'me'" class="flex items-center gap-2.5 px-2 pb-2 pt-1.5">
        <Avatar :image="session.user_image" :label="name" size="lg" />
        <div class="min-w-0">
          <p class="truncate text-sm font-semibold text-ink-gray-9">{{ name }}</p>
          <p v-if="showEmail" class="truncate text-xs text-ink-gray-5">{{ session.user }}</p>
        </div>
      </div>
    </template>
    <button
      type="button"
      class="flex items-center gap-2 rounded-full p-0.5 pr-1.5 transition-colors hover:bg-surface-gray-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
      :aria-label="t('Account menu')"
    >
      <Avatar :image="session.user_image" :label="name" size="md" />
      <FeatherIcon name="chevron-down" class="h-3.5 w-3.5 text-ink-gray-5" />
    </button>
  </Dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { Avatar, Dropdown, FeatherIcon } from 'frappe-ui'
import { session, logoutResource } from '@/data/session'
import { openSettingsDialog } from '@/data/settingsDialog'
import { clearSiteData } from '@/data/clearSiteData'
import { t } from '@/utils/translate'

const name = computed(() => session.full_name || session.user || '')
// the built-in Administrator account's email is its own name: it is shown only once
const showEmail = computed(() => !!session.user && session.user !== name.value)

// Installed as an app (its own window)? Then the Desk would pull the window out of the app.
const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true

const options = computed(() =>
  [
    {
      key: 'me',
      group: name.value,
      items: [
        { label: t('Settings'), icon: 'settings', onClick: openSettingsDialog },
        { label: t('Switch to Desk'), icon: 'grid', onClick: () => window.open('/app', '_self'), hidden: isStandalone },
      ],
    },
    {
      group: t('App'),
      hideLabel: true,
      items: [
        { label: t('Refresh'), icon: 'rotate-cw', onClick: () => window.location.reload() },
        {
          label: t('Clear site data'),
          icon: 'refresh-cw',
          onClick: () => {
            if (window.confirm(t('This clears cached app data and reloads the page. Continue?'))) clearSiteData()
          },
        },
        { label: t('Help'), icon: 'help-circle', onClick: () => window.open('/janadhikara/help', '_self') },
      ],
    },
    { group: t('Account'), hideLabel: true, items: [{ label: t('Logout'), icon: 'log-out', onClick: () => logoutResource.submit() }] },
  ].map((g) => ({ ...g, items: g.items.filter((i) => !i.hidden) })),
)
</script>
