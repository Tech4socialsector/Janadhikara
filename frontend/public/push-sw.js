// Web Push for Janadhikara - pulled into the service worker (see vite.config.js).
// The server's push carries no text: this wakes up, asks for the signed-in
// user's newest unread notification and shows it, so nothing personal travels
// through the browser vendor's push service.

const NOTIFICATIONS_URL =
  '/api/method/janadhikara.notification_prefs.get_my_notifications?limit=1'

function plain(html) {
  return String(html || '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()
}

async function newestUnread() {
  try {
    const response = await fetch(NOTIFICATIONS_URL, { credentials: 'include' })
    const data = (await response.json()).message
    return (data?.notification_logs || []).find((n) => !n.read) || null
  } catch {
    return null
  }
}

function pushUrl(log) {
  if (!log) return '/janadhikara/worklist'
  if (log.document_type === 'ToDo' && log.document_name) return `/janadhikara/todo/${encodeURIComponent(log.document_name)}`
  if (log.document_type === 'Announcement') return '/janadhikara/home'
  if (String(log.link || '').includes('/janadhikara/worklist')) return '/janadhikara/worklist'
  return '/janadhikara/home'
}

self.addEventListener('push', (event) => {
  event.waitUntil(
    (async () => {
      const log = await newestUnread()
      // A browser must show something for every push it receives.
      await self.registration.showNotification('Janadhikara', {
        // Task notices can name a household or person: the lock screen only says a task changed.
        body: !log ? 'You have a new notification' : log.document_type === 'ToDo' ? 'You have a task update. Open the app to see it.' : plain(log.subject || log.title),
        icon: '/assets/janadhikara/default-logo.png',
        badge: '/assets/janadhikara/default-logo.png',
        tag: log ? log.name : 'janadhikara',
        data: { url: pushUrl(log) },
      })
    })(),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/janadhikara/home'
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const client of windows) {
        if (client.url.includes('/janadhikara') && 'focus' in client) {
          await client.focus()
          client.navigate?.(url)
          return
        }
      }
      await self.clients.openWindow(url)
    })(),
  )
})
