// One place that knows whether the device is online, and for a few seconds after the
// connection comes back (so the app can say so and offer to upload what is waiting).
import { computed, ref, watch } from 'vue'
import { useOnline } from '@vueuse/core'

// The phone has a network at all (mobile data / Wi-Fi switched on).
export const hasNetwork = useOnline()

// ...but on 2G / 3G, or a signal so weak the server takes ages to answer, waiting on it makes every
// screen hang. Then the app works from this phone's copy just as with no network (saves are kept here
// too), and checks again now and then. Uploading from Sync Data stays possible: that is the user's call.
const SLOW_TYPES = new Set(['slow-2g', '2g', '3g'])
const info = typeof navigator !== 'undefined' ? navigator.connection : null // Chrome / Android only
const slowType = ref(SLOW_TYPES.has(info?.effectiveType))
info?.addEventListener?.('change', () => (slowType.value = SLOW_TYPES.has(info.effectiveType)))

// Set when a request to our server took too long (see data/offlineApi.js); works on every browser.
const slowReplies = ref(false)
export const slowNetwork = computed(() => hasNetwork.value && (slowType.value || slowReplies.value))

// Good enough to work live: a network, and not a slow one.
export const online = computed(() => hasNetwork.value && !slowNetwork.value)
export const workOffline = () => !online.value

// How long a read may take before the app stops waiting and answers from the phone's copy.
export const SLOW_REPLY_MS = 6000
// A ping slower than this does not count as the connection being good again.
const FAST_PING_MS = 2500
const RECHECK_MS = 30000

let recheck = null
export function markSlowReplies() {
  if (slowReplies.value) return
  slowReplies.value = true
  clearInterval(recheck)
  recheck = setInterval(async () => {
    if (!hasNetwork.value) return
    const started = Date.now()
    if ((await serverReachable(FAST_PING_MS)) && Date.now() - started < FAST_PING_MS) {
      slowReplies.value = false
      clearInterval(recheck)
    }
  }, RECHECK_MS)
}

export const justReconnected = ref(false)

let timer = null
watch(online, (isOnline, wasOnline) => {
  clearTimeout(timer)
  if (isOnline && wasOnline === false) {
    justReconnected.value = true
    timer = setTimeout(() => (justReconnected.value = false), 8000)
  } else {
    justReconnected.value = false
  }
})

// Can our server really be reached right now? `online` only says the phone has a network: Wi-Fi with no
// internet or a very weak signal still counts as online. Asks the server and waits a few seconds at most.
// (`ping` is never answered from the phone's copy - see data/offlineApi.js - nor cached by the service worker.)
export async function serverReachable(timeoutMs = 5000) {
  if (!navigator.onLine) return false
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`/api/method/ping?_=${Date.now()}`, { cache: 'no-store', signal: controller.signal })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}
