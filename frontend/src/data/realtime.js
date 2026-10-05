// Live updates: the server pushes a "notification" event the moment a
// Notification Log is created for the signed-in user (a task assigned to them,
// a mention...). The bell reloads at once, a toast appears, and - when the user
// has allowed it and the app is in the background - a system notification.
import { call, initSocket, toast } from 'frappe-ui'
import { notificationLogs, notificationsResource } from '@/data/notifications'

let started = false
let seen = null

const plain = (html) => {
  const doc = new DOMParser().parseFromString(String(html || ''), 'text/html')
  return (doc.body.textContent || '').replace(/\s+/g, ' ').trim()
}

function announce(log) {
  const text = plain(log.subject || log.title) || 'New notification'
  toast.info(text)
  try {
    if ('Notification' in window && Notification.permission === 'granted' && document.hidden) {
      new Notification('Janadhikara', { body: text, icon: '/assets/janadhikara/default-logo.png', tag: log.name })
    }
  } catch {
    // system notifications are a bonus - the toast and bell still work
  }
}

async function onNotification() {
  await notificationsResource.reload()
  const fresh = notificationLogs.value.filter((n) => !n.read && !seen.has(n.name))
  fresh.forEach((n) => seen.add(n.name))
  // Newest first from the server: announce the latest, the bell shows the rest.
  if (fresh.length) announce(fresh[0])
}

export async function startRealtime() {
  if (started) return
  started = true
  try {
    const res = await call('janadhikara.api.get_realtime_config')
    const config = res?.message ?? res
    if (!config?.site) return
    window.site_name = config.site // frappe-ui builds the socket namespace from this
    const socket = initSocket({ port: config.port })
    // What is already unread at start-up isn't "new".
    await notificationsResource.fetch()
    seen = new Set(notificationLogs.value.map((n) => n.name))
    socket.on('notification', onNotification)
    syncPushSubscription()
  } catch {
    started = false
  }
}

// --- Push alerts (reach the device even when the app is closed) ---------------
const PUSH_WORKER = '/janadhikara/push-worker.js'
const PUSH_SCOPE = '/janadhikara/push-scope/'

const pushSupported = () =>
  'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window

const toKey = (base64) => {
  const padded = (base64 + '='.repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0))
}

// The dedicated push worker (not the app's cached main one): registered once and
// resolved as soon as it is active.
async function pushRegistration() {
  const registration = await navigator.serviceWorker.register(PUSH_WORKER, { scope: PUSH_SCOPE })
  if (registration.active) return registration
  const worker = registration.installing || registration.waiting
  await new Promise((resolve) => {
    if (!worker) return resolve()
    if (worker.state === 'activated') return resolve()
    worker.addEventListener('statechange', () => worker.state === 'activated' && resolve())
  })
  return registration
}

// An older build subscribed through the main worker, which may not have the push
// handler: drop that one so the push worker's subscription is the only one.
async function dropLegacySubscription() {
  try {
    const main = await navigator.serviceWorker.getRegistration('/janadhikara/')
    const old = main && (await main.pushManager.getSubscription())
    if (old) {
      await call('janadhikara.push.remove_push_subscription', { endpoint: old.endpoint })
      await old.unsubscribe()
    }
  } catch {
    // nothing to clean up
  }
}

// Subscribes this browser (asking permission first if needed) and tells the server.
export async function enablePushAlerts() {
  if (!pushSupported()) {
    toast.error('This browser cannot receive push alerts.')
    return false
  }
  const permission = Notification.permission === 'default' ? await Notification.requestPermission() : Notification.permission
  if (permission !== 'granted') {
    toast.error('Alerts are blocked - allow notifications for this site in the browser settings.')
    return false
  }
  await dropLegacySubscription()
  const registration = await pushRegistration()
  const res = await call('janadhikara.push.get_push_config')
  const { public_key } = res?.message ?? res
  let subscription = await registration.pushManager.getSubscription()
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: toKey(public_key),
    })
  }
  await call('janadhikara.push.save_push_subscription', {
    endpoint: subscription.endpoint,
    user_agent: navigator.userAgent,
  })
  toast.success('Alerts are on for this device.')
  return true
}

// Already allowed on this device? Make sure the server knows it (quietly), and move an
// older subscription over to the push worker.
export async function syncPushSubscription() {
  try {
    if (!pushSupported() || Notification.permission !== 'granted') return
    const main = await navigator.serviceWorker.getRegistration('/janadhikara/')
    const legacy = main && (await main.pushManager.getSubscription())
    if (legacy) return enablePushAlerts()
    const registration = await navigator.serviceWorker.getRegistration(PUSH_SCOPE)
    const subscription = registration && (await registration.pushManager.getSubscription())
    if (subscription) {
      await call('janadhikara.push.save_push_subscription', {
        endpoint: subscription.endpoint,
        user_agent: navigator.userAgent,
      })
    }
  } catch {
    // best effort
  }
}

// Should the bell offer "turn on push alerts"? Yes until this device is subscribed.
export async function needsPushSetup() {
  try {
    if (!pushSupported() || Notification.permission === 'denied') return false
    const registration = await navigator.serviceWorker.getRegistration(PUSH_SCOPE)
    return !(registration && (await registration.pushManager.getSubscription()))
  } catch {
    return false
  }
}

export const askForDesktopAlerts = enablePushAlerts

export async function pushStatus() {
  if (!pushSupported()) return 'unsupported'
  if (Notification.permission === 'denied') return 'blocked'
  try {
    const registration = await navigator.serviceWorker.getRegistration(PUSH_SCOPE)
    return registration && (await registration.pushManager.getSubscription()) ? 'on' : 'off'
  } catch {
    return 'off'
  }
}

export async function disablePushAlerts() {
  try {
    const registration = await navigator.serviceWorker.getRegistration(PUSH_SCOPE)
    const subscription = registration && (await registration.pushManager.getSubscription())
    if (!subscription) return
    await call('janadhikara.push.remove_push_subscription', { endpoint: subscription.endpoint })
    await subscription.unsubscribe()
  } catch {
    // nothing to undo
  }
}
