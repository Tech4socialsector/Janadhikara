import { createRouter, createWebHistory, START_LOCATION } from 'vue-router'
import { session, initialUserCheck, userResource } from '@/data/session'
import { modulesResource, findModuleByRoute } from '@/data/modules'
import { settingsEntriesResource, findSettingsEntryByRoute } from '@/data/settingsEntries'
import { setActiveModule } from '@/data/activeModule'
import { queue, queueReady } from '@/data/offlineQueue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
  },
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/worklist',
    name: 'Worklist',
    component: () => import('@/pages/Worklist.vue'),
  },
  {
    path: '/sync-data',
    name: 'SyncData',
    component: () => import('@/pages/SyncData.vue'),
  },
  {
    // Edit a record that is saved on this device and not uploaded yet.
    path: '/sync-data/:offlineId',
    name: 'OfflineEdit',
    component: () => import('@/pages/DoctypeForm.vue'),
    beforeEnter: async (to) => {
      await queueReady
      if (!queue.value.some((i) => i.id === to.params.offlineId)) return { name: 'SyncData' }
    },
    props: (route) => {
      const item = queue.value.find((i) => i.id === route.params.offlineId)
      return { doctype: item?.doctype, name: item?.name, isNew: item?.action === 'insert', offlineId: route.params.offlineId }
    },
    meta: { remountOnParamChange: true },
  },
  {
    path: '/email-accounts',
    name: 'EmailAccountList',
    component: () => import('@/pages/EmailAccountList.vue'),
  },
  {
    path: '/email-accounts/new',
    name: 'EmailAccountNew',
    component: () => import('@/pages/EmailAccountForm.vue'),
    props: { isNew: true },
  },
  {
    path: '/email-accounts/:name',
    name: 'EmailAccountForm',
    component: () => import('@/pages/EmailAccountForm.vue'),
    props: (route) => ({ name: route.params.name }),
    meta: { remountOnParamChange: true },
  },
  {
    path: '/:doctypeRoute',
    name: 'DoctypeList',
    component: () => import('@/pages/DoctypeList.vue'),
    props: (route) => ({ doctype: route.meta.resolvedDoctype }),
    meta: { remountOnParamChange: true },
  },
  {
    path: '/:doctypeRoute/new',
    name: 'DoctypeNew',
    component: () => import('@/pages/DoctypeForm.vue'),
    props: (route) => ({ doctype: route.meta.resolvedDoctype, isNew: true }),
    meta: { remountOnParamChange: true },
  },
  {
    path: '/:doctypeRoute/:name',
    name: 'DoctypeForm',
    component: () => import('@/pages/DoctypeForm.vue'),
    props: (route) => ({ doctype: route.meta.resolvedDoctype, name: route.params.name }),
    meta: { remountOnParamChange: true },
  },
  // Anything else (a mistyped or stale URL, an old bookmark) lands on Home.
  {
    path: '/:pathMatch(.*)*',
    redirect: '/home',
  },
]

let router = createRouter({
  history: createWebHistory('/janadhikara'),
  routes,
})

// Browser Back/Forward (and other in-SPA navigations) never re-check the
// server session on their own - Vue Router just swaps the client-side
// route from cached history state. If the session died server-side (logged
// out in another tab, expired, revoked) while session.user is still
// stale-truthy in memory, beforeEach's own !session.user check below would
// wave the navigation through onto fully-authenticated-looking UI with a
// dead session underneath it.
//
// Awaiting a fresh frappe.auth.get_logged_user call before every single
// in-app navigation (as an earlier version of this did) makes each round
// trip's latency part of every click's critical path - fine on localhost,
// but a real network hop away (e.g. Frappe Cloud) that's enough to make the
// sidebar feel broken, since nothing renders until it resolves. Instead,
// re-validate only when it can actually have changed: when the tab regains
// focus after being hidden (the moment a session could have died
// elsewhere) or after being idle a while, and do it in the background
// rather than blocking the navigation that triggered it - a session that
// really did die gets caught on the very next guard check a moment later,
// without taxing the common case.
const REVALIDATE_INTERVAL_MS = 60_000
let lastCheckedAt = 0

async function recheckAuthIfStale() {
  const now = Date.now()
  if (now - lastCheckedAt < REVALIDATE_INTERVAL_MS) return
  lastCheckedAt = now
  await userResource.fetch().catch(() => {})
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      lastCheckedAt = 0
      userResource.fetch().catch(() => {})
    }
  })
}

// modulesResource requires an authenticated session (it 403s as Guest), and
// this router module loads before login happens - so it must not fetch until
// we know session.user is set, and must actually fetch (not just wait on a
// promise from some earlier, possibly pre-login, call).
let modulesFetch = null
async function ensureModulesLoaded() {
  if (modulesResource.data) return
  if (!modulesFetch) {
    modulesFetch = modulesResource.fetch()
  }
  await modulesFetch.catch(() => {})
}

// Settings-dialog doctypes (Announcement, App Module Setting, ...) aren't in
// any App Module Setting, but still render through the generic list/form
// pages - resolved from the permission-filtered settings entries instead.
let settingsFetch = null
async function ensureSettingsEntriesLoaded() {
  if (settingsEntriesResource.data) return
  if (!settingsFetch) {
    settingsFetch = settingsEntriesResource.fetch()
  }
  await settingsFetch.catch(() => {})
}

router.beforeEach(async (to, from, next) => {
  if (from === START_LOCATION) {
    // On the app's very first navigation, session.user isn't known yet -
    // it's only set once the initial frappe.auth.get_logged_user call
    // resolves. Awaiting that here (a no-op after it's settled) avoids
    // treating "not checked yet" as "logged out" and bouncing a real
    // session to /login.
    await initialUserCheck.catch(() => {})
  } else {
    await recheckAuthIfStale()
  }

  if (to.name !== 'Login' && !session.user) {
    // No ?redirect= - logging in always lands on Home, whatever page was asked for.
    next({ name: 'Login' })
    return
  }
  if (to.name === 'Login' && session.user) {
    next({ name: 'Home' })
    return
  }

  if (session.user) {
    await ensureModulesLoaded()
  }

  // Tasks (ToDo) have no module of their own: /todo/<id> is the task's form, /todo is the Worklist.
  if (to.params.doctypeRoute === 'todo') {
    if (to.name === 'DoctypeList') {
      next({ name: 'Worklist' })
      return
    }
    to.meta.resolvedDoctype = 'ToDo'
    next()
    return
  }

  if (to.params.doctypeRoute) {
    const item = findModuleByRoute(to.params.doctypeRoute)
    if (item) {
      to.meta.resolvedDoctype = item.doctype_name
      // Keep the sidebar's module section in sync while browsing that
      // module's list/form pages, so it persists across navigation there.
      setActiveModule(item.module)
    } else {
      await ensureSettingsEntriesLoaded()
      const entry = findSettingsEntryByRoute(to.params.doctypeRoute)
      if (!entry || entry.is_single) {
        next({ name: 'Home' })
        return
      }
      to.meta.resolvedDoctype = entry.doctype
    }
  }

  next()
})

export default router
