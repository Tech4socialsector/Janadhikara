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
