<template>
  <AppLayout no-sidebar>
    <!-- A soft tinted greeting panel, then every module as a tile (same landing page as the budget app). -->
    <div class="mb-6 rounded-xl bg-gradient-to-br from-blue-50 to-white p-6 dark:from-gray-800/60 dark:to-gray-900">
      <h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ greeting }}</h1>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{{ t('Jump into a module below to get started.') }}</p>
    </div>

    <!-- Announcements: one rounded card at a time (prev/next + dots when
    there are several) so it stays compact on every screen size. A soft
    type-colored gradient, big icon tile and a Dismiss pill keep it light
    without shouting. -->
    <section v-if="current" class="mb-6" :aria-label="t('Announcements')">
      <div
        class="relative overflow-hidden rounded-2xl border p-4 shadow-sm sm:p-5"
        :class="styleFor(current).card"
      >
        <div class="flex items-start gap-3 sm:gap-4">
          <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl sm:h-12 sm:w-12" :class="styleFor(current).icon">
            <FeatherIcon :name="styleFor(current).name" class="h-5 w-5 sm:h-6 sm:w-6" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide" :class="styleFor(current).chip">
                {{ current.announcement_type || 'Info' }}
              </span>
              <span v-if="announcements.length > 1" class="text-xs text-gray-500 dark:text-gray-400">
                {{ index + 1 }} / {{ announcements.length }}
              </span>
            </div>
            <h2 class="mt-1.5 text-base font-semibold leading-snug text-gray-900 dark:text-gray-100">{{ current.title }}</h2>
            <p class="mt-1 whitespace-pre-line text-sm leading-relaxed text-gray-600 dark:text-gray-300">{{ current.message }}</p>

            <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
              <div v-if="announcements.length > 1" class="flex items-center gap-1.5">
                <button
                  v-for="(a, i) in announcements"
                  :key="a.name"
                  class="h-1.5 rounded-full transition-all"
                  :class="i === index ? ['w-5', styleFor(current).dot] : 'w-1.5 bg-gray-300 dark:bg-gray-600'"
                  :aria-label="`Show announcement ${i + 1}`"
                  @click="index = i"
                />
              </div>
              <span v-else />
              <div class="flex items-center gap-2">
                <template v-if="announcements.length > 1">
                  <Button variant="ghost" size="sm" icon="chevron-left" :disabled="index === 0" :tooltip="t('Previous announcement')" :aria-label="t('Previous')" @click="index--" />
                  <Button variant="ghost" size="sm" icon="chevron-right" :disabled="index >= announcements.length - 1" :tooltip="t('Next announcement')" :aria-label="t('Next')" @click="index++" />
                </template>
                <Button v-if="current.dismissible" variant="subtle" size="sm" @click="dismissAnnouncement(current.name)">
                  {{ t('Dismiss') }}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div v-if="modulesResource.loading && !modulesResource.data" class="grid grid-cols-3 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(7rem,max-content))] sm:gap-4">
      <div v-for="i in 6" :key="i" class="flex flex-col items-center gap-2 p-2">
        <Skeleton width="4rem" height="4rem" round />
        <Skeleton width="3.5rem" height="0.75rem" />
      </div>
    </div>
    <div v-else>
      <!-- The modules could not be loaded (usually: no connection and nothing saved yet). -->
      <div
        v-if="modulesResource.error && !modulesResource.data?.length"
        class="mb-5 flex items-start gap-3 rounded-xl border border-outline-amber-1 bg-surface-amber-1 p-4 text-sm"
      >
        <FeatherIcon name="wifi-off" class="mt-0.5 h-5 w-5 flex-shrink-0 text-ink-amber-3" />
        <div>
          <p class="font-semibold text-ink-gray-9">{{ t('Your modules could not be loaded') }}</p>
          <p class="text-ink-gray-6">
            {{ online ? 'Please try again in a moment.' : 'You are offline. Open the app once with internet and it will remember your modules for next time.' }}
            You can still open <b>{{ t('Sync Data') }}</b> below.
          </p>
        </div>
      </div>
      <div
        v-else-if="!modulesResource.data?.length"
        class="mb-5 py-6 text-center text-gray-500 dark:text-gray-400"
      >
        No modules are configured for your account yet. Ask a coordinator to
        add groups in App Module Group.
      </div>

    <!-- Every module as a tile, on every screen size: a wrapping grid, so on a
    phone they're all visible at once (no paging arrows). Tapping one makes it the
    open module - on a phone that opens the menu drawer straight onto that module's
    configured sidebar items, which is why the old inline items list is gone. -->
      <!-- One card per App Module Group (heading, description, tinted by its colour); modules and built-in pages sit inside. -->
      <div class="grid items-start gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-3">
        <section
          v-for="card in cards"
          :key="card.key"
          :id="`group-${card.key}`"
          class="scroll-mt-20 overflow-hidden rounded-2xl border bg-surface-white shadow-sm transition-shadow duration-500"
          :class="highlighted === card.key ? 'border-outline-gray-4 shadow-lg ring-2 ring-outline-gray-3' : 'border-outline-gray-2'"
        >
          <header v-if="card.label" class="flex items-center gap-3 px-3.5 py-2.5 sm:px-4 sm:py-3" :class="card.look.head">
            <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl" :class="card.look.icon">
              <LucideIcon :name="card.icon" class="h-5 w-5" />
            </span>
            <div class="min-w-0">
              <h2 class="truncate text-base font-semibold text-ink-gray-9">{{ t(card.label) }}</h2>
              <p v-if="card.description" class="line-clamp-2 text-xs leading-snug text-ink-gray-6 sm:line-clamp-1 sm:text-sm">{{ t(card.description) }}</p>
            </div>
          </header>
          <div class="grid grid-cols-4 gap-x-1 gap-y-2 p-2.5 sm:grid-cols-3 sm:gap-2 sm:p-3">
            <HomeTile
              v-for="tile in card.tiles"
              :key="tile.key"
              :icon="tile.icon"
              :label="t(tile.label)"
              :to="tile.to"
              :tint="card.look.icon"
              :badge="tile.badge || 0"
              :sync-icon="!!tile.sync"
              @click="tile.click && tile.click()"
            />
          </div>
        </section>
      </div>
    </div>

  </AppLayout>
</template>

<style scoped>
/* The module tiles keep the same physical size on every computer screen (see --ui-tile-scale in index.html); phones keep their own sizes. */
@media (min-width: 640px) {
  html .module-tile-icon {
    width: calc(4.5rem * var(--ui-tile-scale, 1));
    height: calc(4.5rem * var(--ui-tile-scale, 1));
  }
}
@media (prefers-reduced-motion: reduce) {
  .module-tile-icon {
    transition: none !important;
    transform: none !important;
  }
}
</style>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import { FeatherIcon, ErrorMessage, Button } from 'frappe-ui'
import { t } from '@/utils/translate'
import AppLayout from '@/layouts/AppLayout.vue'
import Skeleton from '@/components/Skeleton.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import HomeTile from '@/components/HomeTile.vue'
import { modulesResource } from '@/data/modules'
import { pendingCount } from '@/data/offlineQueue'
import { online } from '@/data/connection'
import { announcementsResource, dismissAnnouncement } from '@/data/announcements'
import { setActiveModule } from '@/data/activeModule'
import { openMobileMenu } from '@/data/mobileMenu'
import { setPageTitle } from '@/data/pageTitle'
import { session } from '@/data/session'

setPageTitle('Home')

const announcements = computed(() => announcementsResource.data || [])
const announcementStyles = {
  Info: {
    name: 'info',
    card: 'border-blue-100 bg-gradient-to-br from-blue-50 to-white dark:border-blue-900/60 dark:from-blue-900/30 dark:to-gray-900',
    icon: 'bg-blue-100 text-blue-600 dark:bg-blue-900/60 dark:text-blue-300',
    chip: 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300',
    dot: 'bg-blue-500',
  },
  Success: {
    name: 'check-circle',
    card: 'border-green-100 bg-gradient-to-br from-green-50 to-white dark:border-green-900/60 dark:from-green-900/30 dark:to-gray-900',
    icon: 'bg-green-100 text-green-600 dark:bg-green-900/60 dark:text-green-300',
    chip: 'bg-green-100 text-green-700 dark:bg-green-900/60 dark:text-green-300',
    dot: 'bg-green-500',
  },
  Warning: {
    name: 'alert-triangle',
    card: 'border-amber-100 bg-gradient-to-br from-amber-50 to-white dark:border-amber-900/60 dark:from-amber-900/30 dark:to-gray-900',
    icon: 'bg-amber-100 text-amber-600 dark:bg-amber-900/60 dark:text-amber-300',
    chip: 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300',
    dot: 'bg-amber-500',
  },
  Urgent: {
    name: 'alert-circle',
    card: 'border-red-100 bg-gradient-to-br from-red-50 to-white dark:border-red-900/60 dark:from-red-900/30 dark:to-gray-900',
    icon: 'bg-red-100 text-red-600 dark:bg-red-900/60 dark:text-red-300',
    chip: 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300',
    dot: 'bg-red-500',
  },
}
const styleFor = (a) => announcementStyles[a.announcement_type] || announcementStyles.Info
const index = ref(0)
const current = computed(() => announcements.value[Math.min(index.value, announcements.value.length - 1)])

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('sm')

const greeting = computed(() => {
  const hour = new Date().getHours()
  const timeGreeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const firstName = (session.full_name || '').split(' ')[0] || session.user
  return firstName ? `${t(timeGreeting)}, ${firstName}` : t(timeGreeting)
})

const router = useRouter()
const route = useRoute()

// Card colours (heading band + icon tint), written out in full so Tailwind keeps them
const LOOKS = {
  Blue: { head: 'bg-blue-50 dark:bg-blue-900/30', icon: 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-300' },
  Green: { head: 'bg-green-50 dark:bg-green-900/30', icon: 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-300' },
  Orange: { head: 'bg-orange-50 dark:bg-orange-900/30', icon: 'bg-orange-100 text-orange-600 dark:bg-orange-900/50 dark:text-orange-300' },
  Purple: { head: 'bg-purple-50 dark:bg-purple-900/30', icon: 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-300' },
  Red: { head: 'bg-red-50 dark:bg-red-900/30', icon: 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-300' },
  Gray: { head: 'bg-surface-gray-2', icon: 'bg-surface-gray-3 text-ink-gray-7' },
}

// On a phone these two are in the bottom navigation, so Home does not repeat them
const PHONE_NAV_PAGES = ['worklist', 'sync-data']

function openItem(mod, item) {
  setActiveModule(mod)
  router.push({ name: 'DoctypeList', params: { doctypeRoute: item.route } })
}
// One card per App Module Group. A group with "Show Sidebar" is one tile that opens it with its sidebar; any other
// group shows each of its DocTypes and pages as a tile of its own that opens directly.
const cards = computed(() => {
  const mods = modulesResource.data || []
  if (!mods.length && modulesResource.error) {
    // The groups could not be loaded at all (offline on a first visit): Sync Data is still offered, so records saved on the device can be uploaded.
    return [{ key: '_offline', label: '', look: LOOKS.Gray, tiles: [{ key: 'sync-data', label: 'Sync Data', icon: 'cloud-upload', to: '/sync-data', sync: true, badge: pendingCount.value }] }]
  }
  return mods
    .map((mod) => ({
      key: mod.name || mod.label,
      label: mod.label,
      description: mod.description,
      icon: mod.icon,
      look: LOOKS[mod.color] || LOOKS.Blue,
      tiles: mod.sidebar
        ? [{ key: 'open', label: t('Open'), icon: mod.icon, click: () => toggleModule(mod) }]
        : (mod.items || [])
            .filter((it) => (it.type === 'Link' && it.route) || (it.type === 'Page' && !(isMobile.value && PHONE_NAV_PAGES.includes(it.route))))
            .map((it) =>
              it.type === 'Page'
                ? { key: `page/${it.route}`, label: it.label, icon: it.icon, to: `/${it.route}`, sync: it.route === 'sync-data', badge: it.route === 'sync-data' ? pendingCount.value : 0 }
                : { key: `${mod.label}/${it.route}`, label: it.label || it.doctype_name, icon: it.icon || mod.icon, click: () => openItem(mod, it) },
            ),
    }))
    .filter((c) => c.tiles.length)
})
// Arriving from a breadcrumb (Home?group=Name): scroll to that group's card and flash it
const highlighted = ref('')
watch(
  [() => route.query.group, () => cards.value.length],
  async ([group]) => {
    if (!group || !cards.value.some((c) => c.key === group)) return
    await nextTick()
    document.getElementById(`group-${group}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    highlighted.value = group
    setTimeout(() => (highlighted.value = ''), 1800)
  },
  { immediate: true },
)

// Links only: section headings and spacers belong to the sidebar.
const firstItem = (mod) => (mod.doctypes || []).find((it) => it.route && it.type !== 'Section Break' && it.type !== 'Spacer')

function toggleModule(mod) {
  if (isMobile.value) {
    // The drawer is the way to browse a module on a phone: pick the module and
    // open the menu on its sidebar items.
    setActiveModule(mod)
    openMobileMenu()
    return
  }
  // A computer: straight into the module's first page; the sidebar appears there with the rest.
  const item = firstItem(mod)
  setActiveModule(mod)
  if (item) router.push({ name: 'DoctypeList', params: { doctypeRoute: item.route } })
}
</script>
