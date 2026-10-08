<template>
  <Dialog v-model="show" :options="{ size: '5xl', title: 'settings-dialog' }">
    <template #body>
      <div class="settings-dialog-panel flex flex-col">
        <div class="flex h-12 flex-shrink-0 items-center gap-1 border-b px-3 dark:border-gray-800 sm:px-4">
          <!-- Phone: inside a section the header gets a back arrow to the list. -->
          <Button
            v-if="mobileScreen === 'panel'"
            class="sm:hidden"
            variant="ghost"
            size="sm"
            icon="arrow-left"
            :tooltip="t('Back')"
            @click="mobileScreen = 'list'"
          />
          <h1 class="min-w-0 flex-1 truncate text-base font-semibold text-gray-900 dark:text-gray-100">
            <span :class="mobileScreen === 'panel' ? 'hidden sm:inline' : ''">{{ t('Settings') }}</span>
            <span v-if="mobileScreen === 'panel'" class="sm:hidden">{{ activeLabel }}</span>
          </h1>
          <Button variant="ghost" size="sm" icon="x" :tooltip="t('Close')" @click="show = false" />
        </div>

        <!-- Phone, first screen: a Settings-app style list - grouped rows with an
        icon tile, the label and a chevron. Tapping one opens that section. -->
        <div v-if="mobileScreen === 'list'" class="min-h-0 flex-1 overflow-y-auto bg-surface-gray-1 px-3 py-3 sm:hidden">
          <div v-for="group in groupedTabs" :key="group.label" class="mb-4">
            <div class="mb-1.5 px-2 text-xs font-medium uppercase tracking-wide text-ink-gray-5">
              {{ group.label }}
            </div>
            <div class="overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-white">
              <button
                v-for="tab in group.tabs"
                :key="tab.key"
                class="flex w-full items-center gap-3 border-b border-outline-gray-1 px-3 py-3 text-left last:border-b-0 active:bg-surface-gray-2"
                @click="openTab(tab.key)"
              >
                <span class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-surface-gray-2 text-ink-gray-7">
                  <component :is="tab.icon" class="h-4 w-4" />
                </span>
                <span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ tab.label }}</span>
                <FeatherIcon name="chevron-right" class="h-4 w-4 flex-shrink-0 text-ink-gray-4" />
              </button>
            </div>
          </div>
        </div>

        <div class="min-h-0 flex-1 sm:flex" :class="mobileScreen === 'list' ? 'hidden' : 'flex'">
          <nav class="hidden w-48 flex-shrink-0 overflow-y-auto border-r px-3 py-4 dark:border-gray-800 sm:block sm:w-56">
            <div v-for="group in groupedTabs" :key="group.label" class="mb-4">
              <div class="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
                {{ group.label }}
              </div>
              <button
                v-for="tab in group.tabs"
                :key="tab.key"
                class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm"
                :class="activeTab === tab.key
                  ? 'bg-gray-100 font-medium text-gray-900 dark:bg-gray-800 dark:text-gray-100'
                  : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800'"
                @click="activeTab = tab.key"
              >
                <component :is="tab.icon" class="h-4 w-4 flex-shrink-0" />
                {{ tab.label }}
              </button>
            </div>
          </nav>

          <div class="min-w-0 flex-1 overflow-y-auto">
            <div class="px-4 py-4 sm:px-8 sm:py-6">
              <ProfilePanel v-if="activeTab === 'profile'" />
              <NotificationSettingsPanel v-else-if="activeTab === 'notifications'" />

              <div v-else-if="activeTab === 'appearance'">
                <div class="mb-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('Appearance') }}</div>
                <TabButtons v-model="theme" :buttons="themeButtons" />
              </div>

              <div v-else-if="activeTab === 'language'">
                <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
                  Choose the app language. It is also the language of your emails and other system text.
                </p>
                <div v-if="languagesResource.loading && !languagesResource.data" class="space-y-1">
                  <Skeleton v-for="i in 6" :key="i" height="2.25rem" />
                </div>
                <div v-else class="flex flex-col gap-1">
                  <button
                    v-for="opt in languagesResource.data"
                    :key="opt.value"
                    class="flex items-center justify-between rounded px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
                    :class="{ 'bg-gray-100 dark:bg-gray-800': appLanguage === opt.value }"
                    @click="selectLanguage(opt.value)"
                  >
                    <span>{{ opt.label }}</span>
                    <FeatherIcon v-if="appLanguage === opt.value" name="check" class="h-4 w-4" />
                  </button>
                </div>
              </div>

              <QuestionConditionsPanel
                v-else-if="activeEntry?.doctype === 'Question Bank'"
                :key="activeEntry.doctype"
                :entry="activeEntry"
                @close="show = false"
              />
              <SettingsDoctypePanel
                v-else-if="activeEntry?.is_single"
                :key="activeEntry.doctype"
                :doctype="activeEntry.doctype"
              />
              <SettingsManagePanel
                v-else-if="activeEntry"
                :key="activeEntry.doctype"
                :entry="activeEntry"
                @close="show = false"
              />
              <EmailSettingsPanel v-else-if="activeTab === 'email-settings'" @close="show = false" />
            </div>
          </div>
        </div>

        <div class="flex flex-shrink-0 justify-end border-t px-4 py-3 dark:border-gray-800">
          <Button icon-left="x" @click="show = false" size="sm">{{ t('Close') }}</Button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<style>
/* Same reasoning as AiAssistant.vue's ai-assistant-panel/data-dialog hook:
frappe-ui's Dialog has no size granular enough for "full-screen on mobile,
centered card on larger screens", and .dialog-overlay/data-dialog (set
from options.title) is the one hook it exposes for a per-dialog override. */
/* 1050, not 50 - also clears Leaflet's own z-index:1000 control pane,
which can otherwise paint through this dialog when it's opened over a page
that has a Geo Location map on it. */
[data-dialog='settings-dialog'].dialog-overlay {
  z-index: 1050;
}

.settings-dialog-panel {
  width: 100%;
  height: 34rem;
  max-height: 80vh;
}

@media (max-width: 639px), (max-height: 480px) {
  [data-dialog='settings-dialog'].dialog-overlay > div {
    padding: 0;
  }
  [data-dialog='settings-dialog'] .dialog-content {
    margin: 0;
    max-width: none;
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }
  .settings-dialog-panel {
    height: 100dvh;
    max-height: none;
  }
}
</style>

<script setup>
import { computed, ref, watch } from 'vue'
import { Dialog, FeatherIcon, TabButtons, Button } from 'frappe-ui'
import { t } from '@/utils/translate'
import SettingsDoctypePanel from '@/components/SettingsDoctypePanel.vue'
import ProfilePanel from '@/components/ProfilePanel.vue'
import NotificationSettingsPanel from '@/components/NotificationSettingsPanel.vue'
import SettingsManagePanel from '@/components/SettingsManagePanel.vue'
import QuestionConditionsPanel from '@/components/QuestionConditionsPanel.vue'
import EmailSettingsPanel from '@/components/EmailSettingsPanel.vue'
import Skeleton from '@/components/Skeleton.vue'
import moduleIcon from '@/components/moduleIcon'
import { session } from '@/data/session'
import { languagesResource, appLanguage, setUserLanguage } from '@/data/language'
import { currentTheme } from '@/data/theme'
import { userContextResource } from '@/data/userContext'
import { settingsEntriesResource } from '@/data/settingsEntries'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const settingsEntries = computed(() => settingsEntriesResource.data || [])
const activeEntry = computed(() => settingsEntries.value.find((e) => e.key === activeTab.value))
const isSystemAdmin = computed(() => !!userContextResource.data?.is_system_admin)

const activeTab = ref('profile')
// Phone only: 'list' (the sections) or 'panel' (one section). Larger screens
// always show the side nav and the panel together.
const mobileScreen = ref('list')
const activeLabel = computed(() => flatTabs.value.find((t) => t.key === activeTab.value)?.label || 'Settings')
function openTab(key) {
  activeTab.value = key
  mobileScreen.value = 'panel'
}

// Reset to the first tab each time the panel is reopened, so a privileged
// user who last viewed an admin-only tab doesn't leave a non-privileged
// session on a blank pane if their role context changes between opens.
watch(show, (visible) => {
  if (visible) {
    activeTab.value = 'profile'
    mobileScreen.value = 'list'
  }
})

const groupedTabs = computed(() => {
  const groups = [
    {
      label: t('Account'),
      tabs: [
        { key: 'profile', label: t('Profile'), icon: moduleIcon('user') },
        { key: 'notifications', label: t('Notifications'), icon: moduleIcon('bell') },
        { key: 'appearance', label: t('Appearance'), icon: moduleIcon('sun') },
        { key: 'language', label: t('Language'), icon: moduleIcon('globe') },
      ],
    },
  ]
  // Everything below "Account" comes from get_settings_entries, already
  // filtered by the user's role permissions on each doctype.
  for (const entry of settingsEntries.value) {
    let group = groups.find((g) => g.label === entry.group)
    if (!group) {
      group = { label: entry.group, tabs: [] }
      groups.push(group)
    }
    group.tabs.push({ key: entry.key, label: entry.label, icon: moduleIcon(entry.icon) })
  }
  if (isSystemAdmin.value) {
    groups.push({
      label: 'Email Settings',
      tabs: [{ key: 'email-settings', label: 'Email Settings', icon: moduleIcon('mail') }],
    })
  }
  return groups
})

// Same tabs as groupedTabs, without the group headers - the mobile strip
// scrolls horizontally instead of grouping vertically, so the grouping
// itself has nowhere to render.
const flatTabs = computed(() => groupedTabs.value.flatMap((group) => group.tabs))

const themeButtons = [
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' },
]

const theme = computed({
  get: () => currentTheme.value,
  set: (v) => (currentTheme.value = v),
})

function selectLanguage(value) {
  setUserLanguage(value)
}
</script>
