<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-30 flex items-stretch justify-around border-t bg-white pb-[env(safe-area-inset-bottom)] dark:border-gray-800 dark:bg-gray-900"
  >
    <router-link
      :to="{ name: 'Home' }"
      class="flex flex-1 flex-col items-center gap-0.5 py-2 text-xs"
      :class="route.name === 'Home' ? 'text-[var(--app-accent)] dark:text-gray-100' : 'text-gray-400 dark:text-gray-500'"
    >
      <FeatherIcon name="home" class="h-5 w-5" />
      {{ t('Home') }}
    </router-link>

    <button
      v-if="assistantConfigResource.data?.enabled"
      class="assistant-nav-item flex flex-1 flex-col items-center gap-0.5 py-2 text-xs text-gray-400 dark:text-gray-500"
      @click="toggleAssistant"
    >
      <span class="assistant-nav-badge relative flex h-5 w-5 items-center justify-center">
        <SparklesIcon class="h-5 w-5" />
      </span>
      {{ t('Assistant') }}
    </button>

    <router-link
      :to="{ name: 'Worklist' }"
      class="flex flex-1 flex-col items-center gap-0.5 py-2 text-xs"
      :class="route.name === 'Worklist' ? 'text-[var(--app-accent)] dark:text-gray-100' : 'text-gray-400 dark:text-gray-500'"
    >
      <FeatherIcon name="check-square" class="h-5 w-5" />
      {{ t('Worklist') }}
    </router-link>

    <!-- Profile: the same hover card as the desktop sidebar, with Settings and
    Log out. Hover opens it; a tap opens it too (and a tap elsewhere closes it). -->
    <UserHoverCard placement="top" with-actions class="flex-1">
      <template #default="{ open, isOpen }">
        <button
          class="flex w-full flex-col items-center gap-0.5 py-2 text-xs text-gray-400 dark:text-gray-500"
          @click="!isOpen && open()"
        >
          <Avatar :image="session.user_image" :label="session.full_name || session.user" size="sm" shape="circle" />
          {{ t('Profile') }}
        </button>
      </template>
    </UserHoverCard>

    <!-- No Menu button here any more: the menu icon in the top header (before the
    logo) opens the same drawer. -->
  </nav>

  <Transition name="menu-overlay">
    <div v-if="showMenu" class="fixed inset-0 z-40 flex items-end bg-black/40" @click.self="showMenu = false">
      <Transition name="menu-sheet" appear>
        <div
          v-if="showMenu"
          role="dialog" aria-modal="true" class="h-[50vh] w-full overflow-y-auto rounded-t-2xl bg-white px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-3 shadow-xl dark:bg-gray-900 dark:ring-1 dark:ring-gray-700"
        >
          <div class="mb-3 flex items-center justify-between">
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ modules.length ? t(modules[0].label) : t('Menu') }}</span>
            <Button variant="ghost" size="sm" icon="x" :aria-label="t('Close')" :tooltip="t('Close')" @click="showMenu = false" />
          </div>
          <div v-if="!modules.length" class="grid grid-cols-4 gap-y-4">
            <button v-for="item in quickLinks" :key="item.key" class="flex min-w-0 flex-col items-center gap-1.5 active:scale-95" @click="item.go">
              <span class="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-gray-600 shadow-sm ring-1 ring-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-700">
                <component :is="item.icon" v-if="item.icon" class="h-6 w-6" />
                <LucideIcon v-else :name="item.lucide" class="h-6 w-6" />
                <span v-if="item.badge" class="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-2xs font-semibold text-white">{{ item.badge }}</span>
              </span>
              <span class="line-clamp-2 max-w-full text-center text-xs leading-tight text-gray-900 dark:text-gray-100">{{ item.label }}</span>
            </button>
          </div>
          <template v-for="mod in modules" :key="mod.label">
            <div class="grid grid-cols-4 gap-y-4">
              <button v-for="item in itemsOf(mod)" :key="item.route" class="flex min-w-0 flex-col items-center gap-1.5 active:scale-95" @click="openItem(item)">
                <span class="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-gray-600 shadow-sm ring-1 ring-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:ring-gray-700"><LucideIcon :name="item.icon || mod.icon" class="h-6 w-6" /></span>
                <span class="line-clamp-2 max-w-full text-center text-xs leading-tight text-gray-900 dark:text-gray-100">{{ t(item.label || item.doctype_name) }}</span>
              </button>
            </div>
          </template>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { showMobileMenu } from '@/data/mobileMenu'
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Avatar, Button, FeatherIcon } from 'frappe-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { activeModule } from '@/data/activeModule'
import { findModuleByRoute } from '@/data/modules'
import { pendingCount } from '@/data/offlineQueue'
import LucideIcon from '@/components/LucideIcon.vue'
import SyncCloudIcon from '@/components/SyncCloudIcon.vue'
import SparklesIcon from '@/components/SparklesIcon.vue'
import UserHoverCard from '@/components/UserHoverCard.vue'
import { showSettingsDialog } from '@/data/settingsDialog'
import { session } from '@/data/session'
import { t } from '@/utils/translate'
import { assistantState, assistantConfigResource, toggleAssistant } from '@/data/aiAssistant'

const route = useRoute()
// Shared with the header's menu button (see data/mobileMenu.js).
const showMenu = showMobileMenu

const router = useRouter()
// Only the module that is open (the one picked on Home or the one the current page belongs to), like the sidebar.
const modules = computed(() => {
  const current = activeModule.value || findModuleByRoute(route.params.doctypeRoute)?.module
  return current ? [current] : []
})
// Links and tiles only: section headings and spacers are a sidebar thing.
const itemsOf = (mod) => (mod.doctypes || []).filter((it) => it.route && it.type !== 'Section Break' && it.type !== 'Spacer')
const goto = (location) => () => {
  showMenu.value = false
  router.push(location)
}
const quickLinks = computed(() => [
  { key: 'home', label: t('Home'), lucide: 'home', go: goto({ name: 'Home' }) },
  { key: 'dashboard', label: t('Dashboard'), lucide: 'layout-dashboard', go: goto({ name: 'Dashboard' }) },
  { key: 'worklist', label: t('Worklist'), lucide: 'check-square', go: goto({ name: 'Worklist' }) },
  { key: 'sync', label: t('Sync Data'), icon: SyncCloudIcon, badge: pendingCount.value > 0 ? (pendingCount.value > 9 ? '9+' : String(pendingCount.value)) : '', go: goto({ name: 'SyncData' }) },
])
function openItem(item) {
  showMenu.value = false
  router.push({ name: 'DoctypeList', params: { doctypeRoute: item.route } })
}

// Close the launcher
// whenever that happens, the same way tapping a link in a mobile drawer
// normally dismisses it.
watch(() => route.fullPath, () => {
  showMenu.value = false
})

// "Settings" (unlike the nav links above) doesn't navigate - it just flips
// this shared ref, so the route watch above never fires for it, leaving
// the drawer open behind the Settings dialog it opens (SettingsDialog
// lives in MobileShell, outside this drawer's own DOM, so it isn't even
// affected by the drawer visually - it's just stuck open underneath).
watch(showSettingsDialog, (open) => {
  if (open) showMenu.value = false
})

// Same reasoning as showSettingsDialog above - the new AI assistant
// trigger in AppSidebar's footer also just flips a shared ref rather than
// navigating.
watch(() => assistantState.visible, (open) => {
  if (open) showMenu.value = false
})
</script>

<style scoped>
.menu-overlay-enter-active,
.menu-overlay-leave-active {
  transition: opacity 0.2s ease;
}
.menu-overlay-enter-from,
.menu-overlay-leave-to {
  opacity: 0;
}

.menu-sheet-enter-active,
.menu-sheet-leave-active {
  transition: transform 0.22s ease;
}
.menu-sheet-enter-from,
.menu-sheet-leave-to {
  transform: translateY(100%);
}


/* "Blinking" as a soft breathing glow rather than a literal opacity
on/off toggle - a hard blink reads as an alert/error state on a button
that's actually just inviting a tap. This item's icon is plain (same
gray-400 outline as Home/Worklist/Alerts, no circular fill like the
desktop sidebar's badge version), so there's no background-color to
echo in a ping ring the way the sidebar/old floating-button versions
did - a small colored ring instead, which reads clearly against the
nav's white/gray-900 background regardless of the icon's own color. */
.assistant-nav-item .assistant-nav-badge {
  animation: assistant-nav-breathe 2.4s ease-in-out infinite;
}
.assistant-nav-badge::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 9999px;
  border: 1.5px solid #6366f1;
  animation: assistant-nav-ping 2.4s ease-out infinite;
  pointer-events: none;
}

@keyframes assistant-nav-breathe {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.12);
  }
}

@keyframes assistant-nav-ping {
  0% {
    opacity: 0.6;
    transform: scale(1);
  }
  100% {
    opacity: 0;
    transform: scale(1.5);
  }
}

@media (prefers-reduced-motion: reduce) {
  .assistant-nav-badge,
  .assistant-nav-badge::after {
    animation: none;
  }
}
</style>
