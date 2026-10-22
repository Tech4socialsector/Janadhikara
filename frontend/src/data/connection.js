// One place that knows whether the device is online, and for a few seconds after the
// connection comes back (so the app can say so and offer to upload what is waiting).
import { ref, watch } from 'vue'
import { useOnline } from '@vueuse/core'

export const online = useOnline()
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
