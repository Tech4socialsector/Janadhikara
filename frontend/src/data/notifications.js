import { computed, reactive } from 'vue'
import { useCall } from 'frappe-ui'
import { session } from '@/data/session'

export const notificationsState = reactive({
  visible: false,
})

export function toggleNotifications() {
  notificationsState.visible = !notificationsState.visible
}

export const notificationsResource = useCall({
  url: '/api/v2/method/janadhikara.notification_prefs.get_my_notifications',
  method: 'GET',
  params: { limit: 20 },
  immediate: false,
  cacheKey: 'janadhikara-notifications',
})

// Only my own notifications: the Administrator account can read every user's logs,
// but "Mark all read" only touches its own - the others' would sit unread forever.
export const notificationLogs = computed(() =>
  (notificationsResource.data?.notification_logs || []).filter((n) => !n.for_user || n.for_user === session.user),
)
export const unreadCount = computed(() => notificationLogs.value.filter((n) => !n.read).length)

const markAllReadCall = useCall({
  url: '/api/v2/method/frappe.desk.doctype.notification_log.notification_log.mark_all_as_read',
  method: 'POST',
  immediate: false,
})

export function markAllRead() {
  markAllReadCall.submit().then(() => notificationsResource.reload())
}

const markReadCall = useCall({
  url: '/api/v2/method/frappe.desk.doctype.notification_log.notification_log.mark_as_read',
  method: 'POST',
  immediate: false,
})

export function markRead(docname) {
  return markReadCall.submit({ docname }).then(() => notificationsResource.reload())
}
