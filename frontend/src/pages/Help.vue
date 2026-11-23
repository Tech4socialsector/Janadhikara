<template>
  <AppLayout>
    <PageHeader>
      <template #title>
        <h1 class="text-lg font-semibold text-ink-gray-9 sm:text-xl">{{ t('User Manual') }}</h1>
        <p class="mt-0.5 text-sm text-ink-gray-5">{{ t('How to use Janadhikara') }}</p>
      </template>
    </PageHeader>

    <div class="flex flex-col gap-6 lg:flex-row">
      <!-- On a phone this becomes a horizontally-scrolling chip row above the content;
      on a laptop it's a sticky side rail, same pattern as a table of contents. -->
      <nav class="lg:sticky lg:top-4 lg:h-fit lg:w-56 lg:flex-shrink-0">
        <div class="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
          <button
            v-for="section in visibleSections"
            :key="section.id"
            class="flex-shrink-0 rounded-lg px-3 py-1.5 text-left text-sm transition-colors lg:flex-shrink"
            :class="activeId === section.id
              ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
              : 'text-ink-gray-6 hover:bg-gray-100 dark:hover:bg-gray-800'"
            @click="scrollTo(section.id)"
          >
            {{ t(section.title) }}
          </button>
        </div>
      </nav>

      <div class="min-w-0 flex-1 space-y-10 pb-16">
        <section id="getting-started" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Getting started') }}</h2>
          <div class="prose-help">
            <p>{{ t('Sign in with the email and password your coordinator gave you, on the sign-in screen. If your organization uses a provider like Google, use the matching "Continue with…" button instead.') }}</p>
            <p>{{ t('Signing in always opens the Home page. From there you can reach every part of the app.') }}</p>
            <ul>
              <li>{{ t('Forgot your password? Use the "Forgot password?" link on the sign-in screen.') }}</li>
              <li>{{ t('On a phone, you can install Janadhikara to your home screen like a regular app. Chrome/Android will offer to install it; on an iPhone, open the Share menu and choose "Add to Home Screen".') }}</li>
            </ul>
          </div>
        </section>

        <section id="home" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Home page') }}</h2>
          <div class="prose-help">
            <p>{{ t('Home shows any announcements from your coordinators, followed by a tile for each module and page you have access to.') }}</p>
            <ul>
              <li>{{ t('Tap a module tile to open it. On a phone this opens a menu of that module\'s record types; on a laptop it expands a row of tiles below.') }}</li>
              <li>{{ t('An announcement can be dismissed if it has a Dismiss button — once dismissed, it won\'t show again for you.') }}</li>
              <li>{{ t('If a module or button you expect is missing, it\'s usually because your role doesn\'t include it yet, not a bug — ask a coordinator.') }}</li>
            </ul>
          </div>
        </section>

        <section id="records" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Viewing and editing records') }}</h2>
          <div class="prose-help">
            <p>{{ t('Opening a module tile or sidebar item shows a list of its records.') }}</p>
            <ul>
              <li>{{ t('Search the list by typing in the search box — it matches the record\'s own fields and anything inside its tables (e.g. searching a person\'s name can find the household that lists them).') }}</li>
              <li>{{ t('Use Filter and Sort to narrow and order the list, and the Columns button to choose which columns show on a laptop.') }}</li>
              <li>{{ t('Tap New to create a record, or tap any row to open it.') }}</li>
              <li>{{ t('Required fields are only checked when you save — you can leave them for later while still editing.') }}</li>
              <li>{{ t('Every dropdown field can be cleared back to "Select option", even a required one, until you save.') }}</li>
              <li>{{ t('Tables inside a form (e.g. a household\'s members) have their own "Search rows" box once they have more than one row.') }}</li>
              <li>{{ t('To attach a photo or document: on a phone this opens your camera directly; on a laptop it offers your webcam, an existing file, or pasting an image link.') }}</li>
              <li>{{ t('Location fields open a map — tap to drop a pin, or draw an area — and fill in the address automatically.') }}</li>
            </ul>
          </div>
        </section>

        <section id="search" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Quick search') }}</h2>
          <div class="prose-help">
            <p>{{ t('Press Ctrl+K (or Cmd+K on a Mac), or tap the search icon, to open quick search from anywhere. It can jump you straight to a module, start a new record, or find a record by name — searching only what you\'re allowed to see.') }}</p>
          </div>
        </section>

        <section id="worklist" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Worklist') }}</h2>
          <div class="prose-help">
            <p>{{ t('Worklist is your list of tasks — things assigned to you, or to someone whose worklist you\'re allowed to view. Switch between a list view and a calendar view, and filter or search like any other list.') }}</p>
          </div>
        </section>

        <section id="dashboard" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Dashboard') }}</h2>
          <div class="prose-help">
            <p>{{ t('Dashboard shows the numbers and charts behind the households and individuals recorded so far. Use its filters to narrow the view, and tap into a number or chart segment to see the exact records behind it.') }}</p>
          </div>
        </section>

        <section id="offline" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Working offline') }}</h2>
          <div class="prose-help">
            <p>{{ t('Janadhikara keeps working without signal:') }}</p>
            <ul>
              <li>{{ t('Anything you\'ve already opened (a list, a record) stays available offline, so a page you\'ve visited before still opens with no connection.') }}</li>
              <li>{{ t('If you try to save a record with no signal, you\'ll be offered "Save offline" — it queues the record on your device.') }}</li>
              <li>{{ t('Open Sync Data to see what\'s waiting, and to upload it once you\'re back online. You can also use Sync Data to download a copy of your records in advance, for working somewhere you know has no signal.') }}</li>
              <li>{{ t('A small dot near the top of the app shows your connection: green for online, amber for a slow connection, red for offline.') }}</li>
            </ul>
          </div>
        </section>

        <section id="ai-assistant" class="scroll-mt-4">
          <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('AI Assistant') }}</h2>
          <div class="prose-help">
            <p>{{ t('If your coordinator has turned it on, an assistant button is available from the sidebar. You can ask it things in plain language — to find a record, summarize counts, or even create or update a record for you — and it can take you straight to the right page.') }}</p>
            <p>{{ t('The assistant can only see and change the same records and fields you yourself are allowed to, and only the record types your administrator has specifically approved it to work with — so it may know less than the whole app on some installations.') }}</p>
          </div>
        </section>

        <template v-if="isPrivileged">
          <div class="flex items-center gap-2 border-t pt-8 dark:border-gray-800">
            <LucideIcon name="shield" class="h-4 w-4 text-ink-gray-5" />
            <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-gray-5">{{ t('For coordinators and administrators') }}</h2>
          </div>

          <section id="admin-setup" class="scroll-mt-4">
            <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Workspace setup') }}</h2>
            <div class="prose-help">
              <p>{{ t('Open Settings from the sidebar to configure the workspace:') }}</p>
              <ul>
                <li>{{ t('App Setting — app name, logo, accent colour, sign-in page text, and the AI Assistant configuration.') }}</li>
                <li>{{ t('App Module Group — the cards on Home: which record types and pages each holds, in what order, with which icon, whether it opens with a sidebar, and which roles can see the group and each item. A group or item with no roles listed is visible to everyone.') }}</li>
                <li>{{ t('Announcement — create a message for the Home page banner, and choose whether it reaches everyone, selected roles, or selected users, with an optional date window and whether it can be dismissed.') }}</li>
                <li>{{ t('Validation Status — the statuses available on survey records (e.g. Completed, Revision Needed), each of which can be restricted to specific roles.') }}</li>
              </ul>
            </div>
          </section>

          <section id="admin-people" class="scroll-mt-4">
            <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('Organizations and workers') }}</h2>
            <div class="prose-help">
              <p>{{ t('Partner Details holds each partner organization. Add or edit its workers in the Employees table on that record — giving a worker an email address automatically creates their sign-in account if one doesn\'t exist yet.') }}</p>
            </div>
          </section>

          <section id="admin-ai" class="scroll-mt-4">
            <h2 class="mb-3 text-base font-semibold text-ink-gray-9">{{ t('AI Assistant data access') }}</h2>
            <div class="prose-help">
              <p>{{ t('Every record type starts with its AI Data Policy disabled, so the assistant cannot read or change it until an administrator deliberately reviews and enables that record type. Enable only what you want the assistant to reach, field by field if needed.') }}</p>
            </div>
          </section>
        </template>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { t } from '@/utils/translate'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { userContextResource } from '@/data/userContext'
import { setPageTitle } from '@/data/pageTitle'

setPageTitle('User Manual')

const isPrivileged = computed(() => !!userContextResource.data?.is_privileged)

const baseSections = [
  { id: 'getting-started', title: 'Getting started' },
  { id: 'home', title: 'Home page' },
  { id: 'records', title: 'Records' },
  { id: 'search', title: 'Quick search' },
  { id: 'worklist', title: 'Worklist' },
  { id: 'dashboard', title: 'Dashboard' },
  { id: 'offline', title: 'Working offline' },
  { id: 'ai-assistant', title: 'AI Assistant' },
]
const adminSections = [
  { id: 'admin-setup', title: 'Workspace setup' },
  { id: 'admin-people', title: 'Organizations & workers' },
  { id: 'admin-ai', title: 'AI data access' },
]
const visibleSections = computed(() => (isPrivileged.value ? [...baseSections, ...adminSections] : baseSections))

const activeId = ref(baseSections[0].id)
function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

let observer
onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((e) => e.isIntersecting)
      if (visible.length) activeId.value = visible[0].target.id
    },
    { rootMargin: '-10% 0px -70% 0px' },
  )
  visibleSections.value.forEach((s) => {
    const el = document.getElementById(s.id)
    if (el) observer.observe(el)
  })
})
onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.prose-help :deep(p) {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: theme('colors.ink.gray.7', #374151);
}
.prose-help :deep(ul) {
  margin-top: 0;
  margin-bottom: 0;
  padding-left: 1.25rem;
  list-style-type: disc;
}
.prose-help :deep(li) {
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: theme('colors.ink.gray.7', #374151);
}
</style>
