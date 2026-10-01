<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-medium text-gray-900 dark:text-gray-100">{{ greeting }}</h1>
      </template>
    </PageHeader>

    <!-- Announcements: one rounded card at a time (prev/next + dots when
    there are several) so it stays compact on every screen size. A soft
    type-colored gradient, big icon tile and a Dismiss pill keep it light
    without shouting. -->
    <section v-if="current" class="mb-6" aria-label="Announcements">
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
                  <Button variant="ghost" size="sm" icon="chevron-left" :disabled="index === 0" aria-label="Previous" @click="index--" />
                  <Button variant="ghost" size="sm" icon="chevron-right" :disabled="index >= announcements.length - 1" aria-label="Next" @click="index++" />
                </template>
                <Button v-if="current.dismissible" variant="subtle" size="sm" @click="dismissAnnouncement(current.name)">
                  Dismiss
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
    <ErrorMessage v-else-if="modulesResource.error" :message="modulesResource.error" />
    <div
      v-else-if="!modulesResource.data || modulesResource.data.length === 0"
      class="py-10 text-center text-gray-500 dark:text-gray-400"
    >
      No modules are configured for your account yet. Ask a coordinator to
      enable modules in App Module Setting.
    </div>

    <!-- Every module as a tile, on every screen size: a wrapping grid, so on a
    phone they're all visible at once (no paging arrows). Tapping one makes it the
    open module - on a phone that opens the menu drawer straight onto that module's
    configured sidebar items, which is why the old inline items list is gone. -->
    <div v-else class="grid grid-cols-3 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(7rem,max-content))] sm:gap-4">
      <!-- Hover a tile (desktop) for a card listing what's inside the module. -->
      <Popover v-for="mod in modulesResource.data" :key="mod.label" trigger="hover" :hover-delay="0.3" placement="bottom-start">
        <template #target>
          <button
            class="module-tile group flex flex-col items-center gap-2 rounded-lg p-2 text-center transition-colors duration-150 hover:bg-gray-100 dark:hover:bg-gray-800"
            :class="{ 'bg-gray-100 dark:bg-gray-800': activeModule?.label === mod.label }"
            @click="toggleModule(mod)"
          >
            <span class="module-tile-icon flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-gray-200 transition-all duration-150 ease-out group-hover:-translate-y-0.5 group-hover:shadow-md group-hover:ring-gray-300 group-active:translate-y-0 group-active:scale-95 group-active:shadow-sm dark:bg-gray-800 dark:ring-gray-700 dark:group-hover:ring-gray-600 sm:h-[4.5rem] sm:w-[4.5rem]">
              <LucideIcon :name="mod.icon" class="h-7 w-7 text-gray-600 transition-colors duration-150 group-hover:text-gray-900 dark:text-gray-300 dark:group-hover:text-gray-100 sm:h-8 sm:w-8" />
            </span>
            <span class="line-clamp-2 text-xs font-medium leading-tight text-gray-900 dark:text-gray-100 sm:text-sm">
              {{ mod.label }}
            </span>
          </button>

        </template>
        <template #body-main>
          <div class="w-56 max-w-[80vw] p-3">
            <div class="mb-1.5 text-sm font-semibold text-ink-gray-9">{{ mod.label }}</div>
            <ul v-if="mod.doctypes?.length" class="space-y-1">
              <li v-for="d in mod.doctypes.slice(0, 8)" :key="d.route" class="flex items-center gap-2 text-sm text-ink-gray-6">
                <LucideIcon :name="d.icon || mod.icon" class="h-3.5 w-3.5 flex-shrink-0" />
                <span class="truncate">{{ d.label || d.doctype_name }}</span>
              </li>
              <li v-if="mod.doctypes.length > 8" class="text-xs text-ink-gray-5">+ {{ mod.doctypes.length - 8 }} more</li>
            </ul>
            <div v-else class="text-sm text-ink-gray-5">Nothing here yet.</div>
          </div>
        </template>
      </Popover>
    </div>

  </AppLayout>
</template>

<style scoped>
@media (prefers-reduced-motion: reduce) {
  .module-tile-icon {
    transition: none !important;
    transform: none !important;
  }
}
</style>

<script setup>
import { computed, ref, watch } from 'vue'
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import { FeatherIcon, ErrorMessage, Button, Popover } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import Skeleton from '@/components/Skeleton.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { modulesResource } from '@/data/modules'
import { announcementsResource, dismissAnnouncement } from '@/data/announcements'
import { activeModule, setActiveModule, clearActiveModule } from '@/data/activeModule'
import { openMobileMenu } from '@/data/mobileMenu'
import { setPageTitle } from '@/data/pageTitle'
import { session } from '@/data/session'

setPageTitle('Home')

const announcements = computed(() => announcementsResource.data || [])
const announcementStyles = {
  Info: {
    name: 'info',
    card: 'border-blue-100 bg-gradient-to-br from-blue-50 to-white dark:border-blue-900/60 dark:from-blue-950/60 dark:to-gray-900',
    icon: 'bg-blue-100 text-blue-600 dark:bg-blue-900/60 dark:text-blue-300',
    chip: 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300',
    dot: 'bg-blue-500',
  },
  Success: {
    name: 'check-circle',
    card: 'border-green-100 bg-gradient-to-br from-green-50 to-white dark:border-green-900/60 dark:from-green-950/60 dark:to-gray-900',
    icon: 'bg-green-100 text-green-600 dark:bg-green-900/60 dark:text-green-300',
    chip: 'bg-green-100 text-green-700 dark:bg-green-900/60 dark:text-green-300',
    dot: 'bg-green-500',
  },
  Warning: {
    name: 'alert-triangle',
    card: 'border-amber-100 bg-gradient-to-br from-amber-50 to-white dark:border-amber-900/60 dark:from-amber-950/60 dark:to-gray-900',
    icon: 'bg-amber-100 text-amber-600 dark:bg-amber-900/60 dark:text-amber-300',
    chip: 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300',
    dot: 'bg-amber-500',
  },
  Urgent: {
    name: 'alert-circle',
    card: 'border-red-100 bg-gradient-to-br from-red-50 to-white dark:border-red-900/60 dark:from-red-950/60 dark:to-gray-900',
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
  return firstName ? `${timeGreeting}, ${firstName}` : timeGreeting
})

function toggleModule(mod) {
  if (isMobile.value) {
    // The drawer is the way to browse a module on a phone: pick the module and
    // open the menu on its sidebar items (tapping the open one just reopens it).
    setActiveModule(mod)
    openMobileMenu()
    return
  }
  if (activeModule.value?.label === mod.label) {
    clearActiveModule()
  } else {
    setActiveModule(mod)
  }
}
</script>
