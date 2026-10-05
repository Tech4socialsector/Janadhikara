<template>
  <div ref="sidebarRef" class="app-sidebar flex h-full flex-shrink-0" @click.capture="logoGoesHome">
    <Sidebar
      v-model:collapsed="collapsed"
      :header="header"
      :sections="sections"
      :disableCollapse="disableCollapse"
    >
      <template #sidebar-item="{ item, isCollapsed: sidebarCollapsed }">
        <hr v-if="item.dividerBefore" class="my-2 border-gray-200 dark:border-gray-800" />
        <!-- A module's sidebar can hold Section Break headings (optionally
        collapsible), Spacers and indented sub-items - see App Module Setting. -->
        <div v-if="item.spacer" class="h-1" />
        <!-- Group heading: reads like frappe-ui's own section label - muted,
        left-aligned, with the fold chevron after the text. A heading that
        can't fold is just a label. -->
        <Button
          v-else-if="item.groupHeader && item.collapsible"
          v-show="!sidebarCollapsed"
          variant="ghost"
          size="sm"
          class="!w-full !justify-start !px-2 text-ink-gray-5"
          data-keep-drawer
          :icon-right="item.closed ? 'chevron-right' : 'chevron-down'"
          @click="toggleGroup(item.groupKey)"
        >
          <template #prefix>
            <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
          </template>
          {{ item.title }}
        </Button>
        <div
          v-else-if="item.groupHeader"
          v-show="!sidebarCollapsed"
          class="flex items-center gap-2 px-2 py-1 text-sm text-ink-gray-5"
        >
          <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
          {{ item.title }}
        </div>
        <div v-else :class="item.indent && !sidebarCollapsed ? 'ml-4 border-l-2 border-outline-gray-2 pl-1' : ''">
          <SidebarItem
            :label="item.label"
            :accessKey="item.accessKey"
            :icon="item.icon"
            :suffix="item.suffix"
            :to="item.to"
            :isActive="item.isActive"
            :onClick="item.onClick"
          />
        </div>
      </template>
      <template #footer-items="{ isCollapsed }">
        <!-- The mobile drawer (embedded) leaves out the assistant card and the
        profile card: on a phone the assistant is in the bottom bar and the
        profile lives in the header (MobileShell). -->
        <Tooltip v-if="!embedded" :text="`Ask ${assistantBotName}`" :disabled="!isCollapsed">
          <button
            v-if="assistantConfigResource.data?.enabled"
            class="assistant-card relative flex w-full items-center gap-2 overflow-hidden rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-2 py-1.5 text-left hover:bg-surface-gray-2"
            :class="{ 'justify-center': isCollapsed }"
            @click="toggleAssistant"
          >
            <span class="assistant-badge flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900">
              <SparklesIcon class="h-3.5 w-3.5" />
            </span>
            <span v-if="!isCollapsed" class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-ink-gray-8">
                {{ assistantBotName }}
              </span>
              <span class="block truncate text-xs text-ink-gray-5">
                Assistant
              </span>
            </span>
          </button>
        </Tooltip>
        <UserHoverCard v-if="!embedded">
          <div class="flex items-center gap-2 rounded px-2 py-1.5" :class="{ 'justify-center': isCollapsed }">
            <Avatar :image="session.user_image" :label="session.full_name || session.user" size="sm" shape="square" />
            <span v-if="!isCollapsed" class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-ink-gray-8">
                {{ session.full_name || session.user }}
              </span>
              <span class="block truncate text-xs text-ink-gray-5">
                {{ session.user }}
              </span>
            </span>
          </div>
        </UserHoverCard>
      </template>
    </Sidebar>
  </div>
  <template v-if="!embedded">
    <NotificationPanel :sidebar-width="collapsed ? '3rem' : '15rem'" :ignore-outside-click="sidebarRef" />
    <SettingsDialog v-model="showSettingsDialog" />
    <AiAssistant />
  </template>
</template>

<style>
/* frappe-ui's Dropdown (used for the account menu above) sets no z-index
of its own - it relies on portal/DOM paint order, which is fine standing
alone on desktop but loses to MobileNav.vue's mobile drawer overlay
(z-40): opening this menu from inside that drawer left it hit-testable
(clicks landed on the right item, confirmed via elementFromPoint) but
not actually visible, since the drawer's own backdrop painted over it.
.dropdown-content itself is position:static (a plain child div) - the
actual position:fixed element that needs the z-index is reka-ui's popper
wrapper one level up, identified by data-reka-popper-content-wrapper
(no class of its own). Not scoped to one dialog instance (unlike
AiAssistant's data-dialog hook) because this wrapper is shared by every
Dropdown/Popover in the app, and all of them should sit above that
drawer for the same reason.

!important because a plain z-index here didn't reliably win in testing -
setting the exact same property to the exact same value via inline style
(equivalent specificity-wise to a scoped attribute selector) did take
effect, so something about this rule's load timing/order relative to the
popper wrapper's own first paint made the plain version unreliable.

1050, not 50: this wrapper backs every Combobox (Link field dropdown) too,
and a form can have both a Link field's dropdown open and a Geo Location
map on the same page - Leaflet's own stylesheet puts its control pane at
z-index 1000, which otherwise painted through a dropdown sitting near the
map (e.g. State's dropdown next to Household profile's map). */
[data-reka-popper-content-wrapper] {
  z-index: 1050 !important;
}

/* Sidebar text, one step smaller than frappe-ui's defaults. frappe-ui's
SidebarItem/SidebarSection/SidebarHeader hardcode text-sm (13px) / text-base
(14px) with no size prop, so they're stepped down here from the outside:
items and section labels 12px, the app/user title 13px, secondary lines 11px.
Scoped to .app-sidebar, so it covers the desktop sidebar, the collapsed
state and the mobile drawer's embedded copy - and nothing else in the app. */
.app-sidebar .text-sm {
  font-size: 12px;
}
.app-sidebar .text-base {
  font-size: 13px;
}
.app-sidebar .text-xs {
  font-size: 11px;
}

/* Branding: the app logo takes 30% of the header row's width (frappe-ui's
SidebarHeader hardcodes it to a 32px tile, with no size prop). The row keeps
its normal height (h-12) - the logo is capped at 2.5rem (the row's vertical
padding is trimmed to fit it) and
uses object-contain, so a wide logo scales to fit rather than being cropped
to a square or making the row taller. The collapsed icon-only sidebar
(w-12) keeps frappe-ui's default tile. */
.app-sidebar > div.w-60 > button.h-12 {
  /* Less vertical padding so a 2.5rem logo fits inside the unchanged h-12 row. */
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
}
.app-sidebar > div.w-60 > button.h-12 > div:first-child {
  width: 30%;
  height: 2.5rem;
  flex-shrink: 0;
}
.app-sidebar > div.w-60 > button.h-12 > div:first-child img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>

<style scoped>
/* The row itself now has a real card surface (border + fill, see the
template) rather than being a plain hover-only row like the other
sidebar items - a soft glow sweeps behind it on a loop via ::before
(z-indexed under the icon/text, which get position:relative + z-index
below) so the whole card reads as "alive," not just the small icon
badge. Kept independent of assistant-badge's own pulse rather than
merged into one animation - they're on different elements. */
.assistant-card {
  animation: assistant-card-glow 3.2s ease-in-out infinite;
}
.assistant-card::before {
  content: '';
  position: absolute;
  inset: -40% -10%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.35), transparent 70%);
  animation: assistant-card-sweep 3.2s ease-in-out infinite;
  pointer-events: none;
}
.assistant-card > * {
  position: relative;
  z-index: 1;
}

@keyframes assistant-card-glow {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0);
  }
  50% {
    box-shadow: 0 0 12px 1px rgba(99, 102, 241, 0.25);
  }
}

@keyframes assistant-card-sweep {
  0%, 100% {
    transform: translateX(-20%);
    opacity: 0.5;
  }
  50% {
    transform: translateX(20%);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .assistant-card,
  .assistant-card::before {
    animation: none;
  }
}

/* Same "breathing glow, not a literal blink" reasoning as MobileNav.vue's
assistant-fab: a hard on/off blink reads as an alert/error state on
something that's just inviting a tap. Ring sized to this badge's own
24px (h-6 w-6), not copy-pasted from the larger floating button. */
.assistant-badge {
  position: relative;
  animation: assistant-badge-breathe 2.4s ease-in-out infinite;
}
.assistant-badge::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  background: #111827;
  animation: assistant-badge-ping 2.4s ease-out infinite;
  pointer-events: none;
}
:global(.dark) .assistant-badge::after {
  background: #f3f4f6;
}

@keyframes assistant-badge-breathe {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.08);
  }
}

@keyframes assistant-badge-ping {
  0% {
    opacity: 0.35;
    transform: scale(1);
  }
  100% {
    opacity: 0;
    transform: scale(1.7);
  }
}

@media (prefers-reduced-motion: reduce) {
  .assistant-badge,
  .assistant-badge::after {
    animation: none;
  }
}
</style>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sidebar, SidebarItem, Avatar, Tooltip, Button } from 'frappe-ui'
import moduleIcon from '@/components/moduleIcon'
import NotificationPanel from '@/components/NotificationPanel.vue'
import UserHoverCard from '@/components/UserHoverCard.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import AiAssistant from '@/components/AiAssistant.vue'
import SparklesIcon from '@/components/SparklesIcon.vue'
import { session, logoutResource } from '@/data/session'
import { clearSiteData } from '@/data/clearSiteData'
import { brandingResource, appLogo } from '@/data/branding'
import { activeModule } from '@/data/activeModule'
import { notificationsResource, unreadCount, toggleNotifications } from '@/data/notifications'
import { pendingCount } from '@/data/offlineQueue'
import SyncCloudIcon from '@/components/SyncCloudIcon.vue'
import { showSettingsDialog, openSettingsDialog } from '@/data/settingsDialog'
import { assistantConfigResource, toggleAssistant } from '@/data/aiAssistant'

const props = defineProps({
  // Forced open (never icon-collapsed) when rendered inside the mobile
  // drawer, where Sidebar's own `isMobile` breakpoint check would otherwise
  // collapse it to icon-only regardless of the drawer's own wider width.
  disableCollapse: { type: Boolean, default: false },
  // The mobile drawer's copy of this component shouldn't render its own
  // NotificationPanel/SettingsDialog - MobileShell already provides a
  // NotificationPanel, and both copies share the same showSettingsDialog
  // state, so rendering a second Dialog here would be a pointless duplicate.
  embedded: { type: Boolean, default: false },
})

const route = useRoute()
const router = useRouter()
const appName = computed(() => brandingResource.data?.app_name || 'Janadhikara')
const assistantBotName = computed(() => assistantConfigResource.data?.bot_name || 'Assistant')
const collapsed = ref(false)

// Clicking the app icon (in the header) goes Home instead of opening the account
// menu; the title / arrow beside it still open the menu.
function logoGoesHome(event) {
  if (!(event.target instanceof Element)) return
  if (!event.target.closest('.app-sidebar > div > button.h-12 img')) return
  event.preventDefault()
  event.stopPropagation()
  router.push({ name: 'Home' })
}
const sidebarRef = ref(null)

notificationsResource.fetch()

// Installed as an app (standalone window)? Then "Help" (external docs) and "Go to
// Desk" (a different site area) would drag the window out of the app, and the
// browser's address bar comes back with them - so they're left out there.
const isStandalone =
  window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true
const LEAVES_THE_APP = new Set(['Help', 'Go to Desk'])

const header = computed(() => ({
  title: appName.value,
  subtitle: session.full_name || session.user,
  logo: appLogo.value || null,
  menuItems: [
    {
      label: 'Settings',
      icon: 'settings',
      onClick: openSettingsDialog,
    },
    {
      label: 'Help',
      icon: 'help-circle',
      onClick: () => window.open('https://frappeframework.com/docs', '_blank', 'noopener'),
    },
    {
      label: 'Clear site data',
      icon: 'refresh-cw',
      onClick: () => {
        if (window.confirm('This clears cached app data and reloads the page. Continue?')) {
          clearSiteData()
        }
      },
    },
    {
      label: 'Go to Desk',
      icon: 'grid',
      onClick: () => window.open('/app', '_self'),
    },
    {
      label: 'Logout',
      icon: 'log-out',
      onClick: () => logoutResource.submit(),
    },
  ].filter((item) => !(isStandalone && LEAVES_THE_APP.has(item.label))),
}))

// Which Section Break groups of the open module are folded up (by key). Groups
// start open; the folds reset whenever another module is opened.
const collapsedGroups = ref(new Set())
watch(activeModule, () => {
  collapsedGroups.value = new Set()
})
function toggleGroup(key) {
  const next = new Set(collapsedGroups.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  collapsedGroups.value = next
}

// A module's sidebar as rows: Links, Section Break headings, Spacers, with a
// Link able to be a child (indented sub-item) of the item above it. A group is
// its heading plus the child items under it - the first ordinary (non-child)
// Link or the next heading ends it - so folding a group hides only its own
// children. Older module data without `items` falls back to the plain list of
// doctypes. `keyPrefix` keeps each group's fold key unique.
function buildModuleRows(mod, keyPrefix) {
  const items = mod.items || (mod.doctypes || []).map((d) => ({ type: 'Link', ...d }))
  const rows = []
  let folded = false
  items.forEach((it, index) => {
    if (it.type === 'Section Break') {
      const key = `${keyPrefix}${index}`
      folded = !!it.collapsible && collapsedGroups.value.has(key)
      rows.push({
        // unique per row - the sidebar keys its items by `label`
        label: `__group-${key}`,
        groupHeader: true,
        groupKey: key,
        title: it.label,
        // The heading's own icon (a folder when none is set), like every item.
        icon: moduleIcon(it.icon || 'folder'),
        collapsible: !!it.collapsible,
        closed: folded,
      })
    } else if (it.type === 'Spacer') {
      // Just a gap - it doesn't end a group (a spacer between a heading and its
      // children is common), and it folds away along with the group it's in.
      // No gap straight after a heading - the heading and its children read as one block.
      if (!folded && !rows[rows.length - 1]?.groupHeader) rows.push({ label: `__spacer-${keyPrefix}${index}`, spacer: true })
    } else {
      if (!it.child) folded = false
      if (folded) return
      rows.push({
        label: it.label || it.doctype_name,
        icon: moduleIcon(it.icon || mod.icon),
        to: { name: 'DoctypeList', params: { doctypeRoute: it.route } },
        isActive: route.params.doctypeRoute === it.route,
        indent: !!it.child,
      })
    }
  })
  return rows
}

const sections = computed(() => {
  const sectionList = [
    {
      label: '',
      items: [
        {
          label: 'Notifications',
          icon: moduleIcon('bell'),
          suffix: unreadCount.value > 0 ? String(unreadCount.value > 9 ? '9+' : unreadCount.value) : undefined,
          onClick: toggleNotifications,
        },
        {
          label: 'Home',
          icon: moduleIcon('home'),
          to: { name: 'Home' },
          dividerBefore: true,
          isActive: route.name === 'Home',
        },
        {
          label: 'Worklist',
          icon: moduleIcon('check-square'),
          to: { name: 'Worklist' },
          isActive: route.name === 'Worklist',
        },
        {
          label: 'Sync Data',
          icon: SyncCloudIcon,
          to: { name: 'SyncData' },
          suffix: pendingCount.value > 0 ? String(pendingCount.value > 9 ? '9+' : pendingCount.value) : undefined,
          isActive: route.name === 'SyncData',
        },
      ],
    },
  ]


  // Only the open module's items - its Links, Section Break groups (each with
  // its indented child items) and Spacers - on desktop and on a phone alike.
  if (activeModule.value) {
    const mod = activeModule.value
    sectionList.push({ label: mod.label, items: buildModuleRows(mod, 'g') })
  }

  return sectionList
})
</script>
