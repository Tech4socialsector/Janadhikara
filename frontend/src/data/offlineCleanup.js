// When the connection comes back nothing is uploaded on its own: records saved offline stay
// (encrypted) until the user uploads them from Sync Data. The downloaded copy stays too, so the
// app keeps working the next time the signal drops; it is removed on sign-out (data/session.js),
// by "Remove" on Sync Data, or when someone else signs in on this phone.
import { watch } from 'vue'
import { toast } from 'frappe-ui'
import { online } from '@/data/connection'
import { queue, queueReady } from '@/data/offlineQueue'

let started = false
export function startAutoCleanup() {
  if (started) return
  started = true
  watch(online, async (isOnline, wasOnline) => {
    if (!(isOnline && wasOnline === false)) return
    // the browser can claim "online" while the server is still out of reach: remind only once it answers
    const reachable = await fetch('/api/method/ping', { cache: 'no-store' }).then((r) => r.ok, () => false)
    if (reachable && queue.value.length) {
      toast.info(`Back online - ${queue.value.length} saved record${queue.value.length === 1 ? ' is' : 's are'} waiting. Open Sync Data to upload.`)
    }
  })
  // Opened with a connection while saved records from an offline session are still here:
  // just remind - the upload is the user's call.
  queueReady.then(() => {
    if (online.value && queue.value.length) {
      toast.info(`${queue.value.length} saved record${queue.value.length === 1 ? ' is' : 's are'} waiting to upload. Open Sync Data.`)
    }
  })
}
