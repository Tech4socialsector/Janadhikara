// When the connection comes back, the device is tidied - but nothing is uploaded on its
// own: records saved offline stay (encrypted) until the user uploads them from Sync Data.
//   1. the downloaded reference data (and the stored icon) is removed;
//   2. once no saved record is left either, the encryption key is removed too.
import { watch } from 'vue'
import { toast } from 'frappe-ui'
import { online } from '@/data/connection'
import { queue, queueReady } from '@/data/offlineQueue'
import { removePack, packInfo } from '@/data/offlinePack'
import { dropKey } from '@/data/deviceCrypto'

let running = false
export async function cleanupDevice() {
  if (running) return
  running = true
  try {
    const hadPack = !!packInfo.value
    await removePack()
    if (!queue.value.length) await dropKey()
    const waiting = queue.value.length
    if (waiting) {
      toast.info(`Back online - ${waiting} saved record${waiting === 1 ? ' is' : 's are'} waiting. Open Sync Data to upload.`)
    } else if (hadPack) {
      toast.info('Back online - the offline copy was removed from this device.')
    }
  } finally {
    running = false
  }
}

let started = false
export function startAutoCleanup() {
  if (started) return
  started = true
  watch(online, (isOnline, wasOnline) => {
    if (isOnline && wasOnline === false) cleanupDevice()
  })
  // Opened with a connection while saved records from an offline session are still here:
  // just remind - the upload is the user's call.
  queueReady.then(() => {
    if (online.value && queue.value.length) {
      toast.info(`${queue.value.length} saved record${queue.value.length === 1 ? ' is' : 's are'} waiting to upload. Open Sync Data.`)
    }
  })
}
