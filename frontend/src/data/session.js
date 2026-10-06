import { reactive } from 'vue'
import { createResource, setConfig, frappeRequest } from 'frappe-ui'
import router from '@/router'
import { clearSnapshots } from '@/data/localSnapshot'

// createResource() below fires an immediate fetch at module-evaluation time
// (see initialUserCheck) - that's before main.js reaches its own
// setConfig('resourceFetcher', ...) call, since importing this module (via
// App.vue) happens as part of resolving main.js's imports, ahead of any of
// main.js's executable statements. Without the resourceFetcher configured
// yet, createResource falls back to a raw fetch with no /api/method/
// prefixing, silently mis-resolving relative URLs against the current
// route instead of the site root. Configuring it here, at first point of
// use, guarantees it's set before any resource in this app can fetch.
setConfig('resourceFetcher', frappeRequest)

// `window.user` is set by frappe-ui's jinjaBootData Vite plugin from the
// www/janadhikara.html Jinja context's `boot` dict in production builds
// only - it's just a first-paint optimization. userResource.fetch() below
// is the authoritative check.
export const session = reactive({
  user: window.user && window.user !== 'Guest' ? window.user : null,
  user_language: null,
  user_image: null,
  full_name: null,
})

const LAST_USER = 'janadhikara-last-user'
const rememberUser = (user) => {
  try {
    if (user && user !== 'Guest') localStorage.setItem(LAST_USER, user)
  } catch {
    // not remembered
  }
}
const rememberedUser = () => {
  try {
    return localStorage.getItem(LAST_USER) || null
  } catch {
    return null
  }
}
// Signed out: nothing of the last user may linger on the device (the saved page shell and
// cached reads carry their name and data).
async function forgetDevice() {
  try {
    localStorage.removeItem(LAST_USER)
    clearSnapshots()
    const worker = (await navigator.serviceWorker?.getRegistration('/janadhikara/'))?.active
    worker?.postMessage('janadhikara-clear-caches')
    await Promise.all(['janadhikara-shell', 'janadhikara-api-reads'].map((name) => caches.delete(name)))
  } catch {
    // best effort
  }
}

export const userResource = createResource({
  url: 'frappe.auth.get_logged_user',
  cache: 'frappe-user',
  onError(error) {
    // No connection is not "signed out": keep the user this device last saw, so the app
    // still opens offline. A real rejection from the server does sign them out.
    if (!navigator.onLine || error instanceof TypeError || /failed to fetch|network|load failed/i.test(String(error?.message || error))) {
      if (!session.user) session.user = rememberedUser()
      return
    }
    session.user = null
  },
  onSuccess(user) {
    session.user = user
    rememberUser(user)
    fetchUserLanguage()
  },
})

// `window.user` boot data isn't actually present on every real page load
// (only wired up for certain production render paths), so on a hard
// reload/direct navigation `session.user` starts out null until this fetch
// resolves. The router's navigation guard runs synchronously before that -
// without awaiting this promise it would treat "not yet known" the same as
// "logged out" and bounce a genuinely logged-in user to /login. App.vue
// kicks this off once on mount; the router guard awaits it on the app's
// first navigation only (see initialAuthCheck in router.js).
export const initialUserCheck = userResource.fetch()

export const userLanguageResource = createResource({
  url: 'frappe.client.get_value',
  makeParams: () => ({
    doctype: 'User',
    filters: session.user,
    fieldname: ['language', 'user_image', 'full_name'],
  }),
  onSuccess(data) {
    session.user_language = data?.language || null
    session.user_image = data?.user_image || null
    session.full_name = data?.full_name || null
  },
})

function fetchUserLanguage() {
  if (session.user) userLanguageResource.reload()
}

export const loginResource = createResource({
  url: 'login',
  makeParams({ email, password }) {
    return {
      usr: email,
      pwd: password,
    }
  },
  onSuccess() {
    loginResource.error = null
    userResource.reload().then(() => {
      router.replace({ name: 'Home' })
    })
  },
})

export const logoutResource = createResource({
  url: 'logout',
  async onSuccess() {
    session.user = null
    userResource.reset()
    await forgetDevice()
    window.location.reload()
  },
})

export function isLoggedIn() {
  return Boolean(session.user)
}
