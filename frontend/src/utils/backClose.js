import { watch } from 'vue'

// The phone's Back button (and the browser's) closes an open sheet, dialog or panel first,
// instead of leaving the page behind it.
//
// An overlay that registers here pushes one history entry while it is open. Back removes that entry
// and the overlay closes; closing it any other way (its X, a tap outside) removes the entry again.
// If the app navigates while overlays are open (a tile in the menu, a search result), the
// entries are removed first and the navigation then goes ahead, so no extra Back press is needed.
const stack = [] // overlays that currently own a history entry, innermost last
let counter = 0

export function useBackToClose(open) {
  const id = ++counter
  const entry = { id, close: () => (open.value = false) }
  watch(
    open,
    (isOpen) => {
      const index = stack.indexOf(entry)
      if (isOpen && index < 0) {
        history.pushState({ ...history.state, overlay: id }, '')
        stack.push(entry)
      } else if (!isOpen && index >= 0) {
        stack.splice(index, 1)
        // Removed on the next tick, and only if the overlay's entry is still the current one: when a page change
        // started at the same moment (a tile that closes the menu and navigates), going back would undo it.
        setTimeout(() => {
          if (history.state?.overlay === id) history.back()
        }, 0)
      }
    },
    { flush: 'sync' },
  )
}

// Back pressed: close every overlay whose history entry is gone.
if (typeof window !== 'undefined') {
  window.addEventListener('popstate', () => {
    const current = history.state?.overlay
    while (stack.length && stack[stack.length - 1].id !== current) stack.pop().close()
  })
}

export function installOverlayGuard(router) {
  router.beforeEach((to, from) => {
    if (!stack.length || to.fullPath === from.fullPath) return
    const count = stack.length
    stack.splice(0).forEach((entry) => entry.close())
    history.go(-count)
    // Go on to the page once the entries are gone. If the browser never reports that (some do not), go on anyway,
    // so a tap on a menu item can never end with nothing opening.
    let went = false
    const proceed = () => {
      if (went) return
      went = true
      router.push(to.fullPath)
    }
    window.addEventListener('popstate', proceed, { once: true })
    setTimeout(proceed, 500)
    return false
  })
}
