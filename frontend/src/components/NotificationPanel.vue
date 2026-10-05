<template>
  <!-- Notifications as a popup, laid out like a WhatsApp / Telegram chat list:
  a round avatar, the title in bold with the time on the right, a one-line
  preview underneath and a green unread badge. Full screen on phones. -->
  <Dialog v-model="show" :options="{ size: 'md', title: 'notifications-dialog' }">
    <template #body>
      <div class="notifications-panel flex flex-col">
        <div class="flex items-center justify-between px-4 pb-2 pt-4">
          <h2 class="text-lg font-semibold text-ink-gray-9">Notifications</h2>
          <div class="flex items-center gap-1">
            <Button
              v-if="unreadCount > 0"
              variant="ghost"
              size="sm"
              icon-left="check-circle"
              @click="markAllRead"
            >
              Mark all read
            </Button>
            <Button variant="ghost" size="sm" icon="x" tooltip="Close" @click="show = false" />
          </div>
        </div>

        <!-- Filter chips, like Telegram's folders / WhatsApp's All-Unread. -->
        <div class="flex items-center gap-2 px-4 pb-3">
          <Button size="sm" :variant="filter === 'all' ? 'subtle' : 'ghost'" @click="filter = 'all'">All</Button>
          <Button size="sm" :variant="filter === 'unread' ? 'subtle' : 'ghost'" @click="filter = 'unread'">
            Unread
            <template v-if="unreadCount > 0" #suffix>
              <span class="flex h-4 min-w-4 items-center justify-center rounded-full bg-[#25d366] px-1 text-2xs font-semibold text-white">
                {{ unreadCount }}
              </span>
            </template>
          </Button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto border-t border-outline-gray-1">
          <div v-if="notificationsResource.loading && !notificationsResource.data" class="space-y-1 p-4">
            <div v-for="i in 5" :key="i" class="flex items-center gap-3 py-2">
              <Skeleton width="3rem" height="3rem" round />
              <div class="flex-1 space-y-2">
                <Skeleton width="55%" height="0.8rem" />
                <Skeleton width="85%" height="0.65rem" />
              </div>
            </div>
          </div>

          <div
            v-else-if="visibleLogs.length === 0"
            class="flex flex-col items-center gap-3 px-6 py-20 text-center text-ink-gray-5"
          >
            <span class="flex h-16 w-16 items-center justify-center rounded-full bg-surface-gray-2">
              <FeatherIcon name="bell" class="h-7 w-7" />
            </span>
            <span class="text-base font-medium text-ink-gray-7">
              {{ filter === 'unread' ? "You're all caught up" : 'No notifications yet' }}
            </span>
            <span class="text-sm">
              {{ filter === 'unread' ? 'Nothing unread right now.' : 'Mentions, assignments and shares will show up here.' }}
            </span>
          </div>

          <button
            v-for="n in visibleLogs"
            :key="n.name"
            type="button"
            class="chat-row group flex w-full items-center gap-3 px-4 text-left hover:bg-surface-gray-1"
            @click="open(n)"
          >
            <span
              class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full text-base font-semibold text-white"
              :style="{ backgroundColor: avatarColor(n) }"
            >
              <template v-if="initials(n)">{{ initials(n) }}</template>
              <FeatherIcon v-else :name="iconName(n)" class="h-5 w-5" />
            </span>

            <span class="chat-row-body min-w-0 flex-1 border-b border-outline-gray-1 py-3">
              <span class="flex items-baseline justify-between gap-2">
                <span
                  class="truncate text-base text-ink-gray-9"
                  :class="n.read ? 'font-medium' : 'font-semibold'"
                >
                  {{ senderName(n) }}
                </span>
                <span class="flex-shrink-0 text-xs" :class="n.read ? 'text-ink-gray-5' : 'font-medium text-[#25d366]'">
                  {{ formatTime(n.creation) }}
                </span>
              </span>
              <span class="mt-0.5 flex items-center justify-between gap-2">
                <span class="truncate text-sm" :class="n.read ? 'text-ink-gray-5' : 'text-ink-gray-7'">
                  {{ preview(n) }}
                </span>
                <span
                  v-if="!n.read"
                  class="flex h-5 min-w-5 flex-shrink-0 items-center justify-center rounded-full bg-[#25d366] px-1 text-2xs font-semibold text-white"
                >
                  1
                </span>
              </span>
            </span>
          </button>
        </div>

        <div class="flex flex-shrink-0 justify-end border-t border-outline-gray-1 px-4 py-3">
          <Button icon-left="x" @click="show = false" size="sm">Close</Button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<style>
/* Popup size and, on phones, full screen - same hook the other dialogs use
(the data-dialog attribute frappe-ui sets from options.title). */
[data-dialog='notifications-dialog'].dialog-overlay {
  z-index: 1050;
}
.notifications-panel {
  width: 100%;
  height: 36rem;
  max-height: 85vh;
}
.notifications-panel .chat-row {
  min-height: 4.5rem;
}
@media (max-width: 639px) {
  [data-dialog='notifications-dialog'].dialog-overlay > div {
    padding: 0;
  }
  [data-dialog='notifications-dialog'] .dialog-content {
    margin: 0;
    max-width: none;
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }
  .notifications-panel {
    height: 100dvh;
    max-height: none;
  }
}
</style>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog, FeatherIcon, Button } from 'frappe-ui'
import Skeleton from '@/components/Skeleton.vue'
import {
  notificationsState,
  notificationsResource,
  notificationLogs,
  unreadCount,
  markAllRead,
  markRead,
} from '@/data/notifications'
import { findModuleByDoctype } from '@/data/modules'

// Kept so existing callers that still pass them (the old side-panel layout
// needed the sidebar width / an element to ignore) don't break - a popup has
// no use for either.
defineProps({
  sidebarWidth: { type: String, default: '15rem' },
  ignoreOutsideClick: { type: [Object, String], default: null },
})

const router = useRouter()
const filter = ref('all')

const show = computed({
  get: () => notificationsState.visible,
  set: (value) => (notificationsState.visible = value),
})

const visibleLogs = computed(() =>
  filter.value === 'unread' ? notificationLogs.value.filter((n) => !n.read) : notificationLogs.value,
)

// Notification text is HTML from the server - shown as plain text only.
function plain(html) {
  if (!html) return ''
  const doc = new DOMParser().parseFromString(String(html), 'text/html')
  return (doc.body.textContent || '').replace(/\s+/g, ' ').trim()
}

const TYPE_ICONS = {
  Mention: 'at-sign',
  Assignment: 'user-check',
  Share: 'share-2',
  Alert: 'alert-circle',
  'Energy Point': 'zap',
}
const iconName = (n) => TYPE_ICONS[n.type] || 'bell'

// "Who" the notification is from: the sending user's name when known,
// otherwise the notification's own title (which is what the old panel led with).
function senderName(n) {
  if (n.from_user) {
    const local = String(n.from_user).split('@')[0]
    return local.replace(/[._-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
  return plain(n.title || n.subject) || 'Notification'
}

function preview(n) {
  const body = plain(n.description || n.email_content)
  if (n.from_user) return body || plain(n.title || n.subject)
  return body || n.type || ''
}

function initials(n) {
  if (!n.from_user) return ''
  const words = senderName(n).split(' ').filter(Boolean)
  return ((words[0]?.[0] || '') + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase()
}

const AVATAR_COLORS = ['#e17076', '#7bc862', '#e5ca77', '#65aadd', '#a695e7', '#ee7aae', '#6ec9cb', '#faa774']
function avatarColor(n) {
  const key = n.from_user || n.type || n.name || ''
  let hash = 0
  for (const ch of String(key)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

// WhatsApp-style stamps: today's time, "Yesterday", then the date.
function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const today = new Date()
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const days = Math.round((startOfToday - new Date(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000)
  if (days <= 0) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  if (days === 1) return 'Yesterday'
  if (days < 7) return date.toLocaleDateString([], { weekday: 'long' })
  return date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function open(n) {
  if (!n.read) markRead(n.name)
  const mod = n.document_type ? findModuleByDoctype(n.document_type) : null
  if (mod && n.document_name) {
    router.push({
      name: 'DoctypeForm',
      params: { doctypeRoute: mod.route, name: n.document_name },
    })
    notificationsState.visible = false
  }
}
</script>
