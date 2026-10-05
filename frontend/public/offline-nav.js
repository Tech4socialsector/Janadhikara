// Opening ANY page of the app with no connection (a bookmark, the installed app, a link)
// must still start the app - not the browser's "This site can't be reached".
//
// The app is a single-page app: every /janadhikara/... address is the same HTML shell, and
// the router inside it decides what to show. So: while online, keep the latest shell; when a
// navigation fails (no connection, or too slow), serve that shell, whatever the address.
// (Registered before Workbox's own handlers, see importScripts in vite.config.js.)
const SHELL_CACHE = 'janadhikara-shell'
const SHELL_KEY = '/janadhikara/__shell'
const NETWORK_WAIT_MS = 6000

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('timeout')), ms)
    promise.then(
      (value) => {
        clearTimeout(timer)
        resolve(value)
      },
      (error) => {
        clearTimeout(timer)
        reject(error)
      },
    )
  })
}

async function shell(request) {
  const cache = await caches.open(SHELL_CACHE)
  try {
    const response = await withTimeout(fetch(request), NETWORK_WAIT_MS)
    const isHtml = (response.headers.get('content-type') || '').includes('text/html')
    // Only a normal page (not a redirect to /login or an error) becomes the saved shell.
    if (response.ok && isHtml && !response.redirected) await cache.put(SHELL_KEY, response.clone())
    return response
  } catch {
    return (await cache.match(SHELL_KEY)) || Response.error()
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.mode !== 'navigate') return
  const url = new URL(request.url)
  if (!url.pathname.startsWith('/janadhikara')) return
  // The service-worker files themselves are not pages.
  if (/\.(js|map)$/.test(url.pathname)) return
  event.respondWith(shell(request))
})

// Signed out: forget the saved shell (it carries the signed-in user's name).
self.addEventListener('message', (event) => {
  if (event.data === 'janadhikara-clear-caches') {
    event.waitUntil(Promise.all([caches.delete(SHELL_CACHE), caches.delete('janadhikara-api-reads')]))
  }
})
