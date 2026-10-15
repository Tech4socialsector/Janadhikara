// The one place everything for working with no connection is kept on this phone.
//
// A single download (janadhikara.offline.get_offline_data) brings everything the signed-in person may
// read: their own Settlements, Households and Individuals in full, and the masters, partners and
// linked records as field data. It is stored here, one table per doctype, each compressed and then
// encrypted, in one IndexedDB database - and every screen reads it from here (lists, records, link
// pickers, search, dashboard) through data/offlineApi.js. No files or photos. Started only by the
// button on Sync Data; removed on sign-out, on "Remove", or when someone else signs in on this phone.
import { ref } from 'vue'
import { call } from 'frappe-ui'
import { encryptBytes, decryptBytes, encryptJson, decryptJson } from '@/data/deviceCrypto'

const DB_NAME = 'janadhikara-data'
const STORE = 'kv'
const INFO = 'info'
const ICON = 'icon'
const tableKey = (doctype) => `t:${doctype}`

// { user, generated, bytes, counts: { Doctype: n }, children: [child-table doctypes], metaDoctypes }
export const storeInfo = ref(null)
export const storeState = ref({ downloading: false, step: '', percent: 0, error: null })
// The app's own icon, kept so the header still shows it with no connection (the only image stored).
export const appIconDataUrl = ref(null)
const memory = new Map() // doctype -> { title_field, istable, docs }, read once and kept

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}
const tx = async (mode, work) => {
  const db = await openDb()
  try {
    return await new Promise((resolve, reject) => {
      const t = db.transaction(STORE, mode)
      const request = work(t.objectStore(STORE))
      t.oncomplete = () => resolve(request?.result)
      t.onerror = () => reject(t.error)
    })
  } finally {
    db.close()
  }
}

const gzip = async (text) => new Response(new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer()
const gunzip = async (buffer) => new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).text()

// Compressed, then encrypted: as small as it can be. Returns the stored size.
async function writeTable(doctype, table) {
  const compressed = await gzip(JSON.stringify(table))
  const enc = await encryptBytes(new Uint8Array(compressed))
  await tx('readwrite', (s) => s.put(enc, tableKey(doctype)))
  memory.set(doctype, table)
  return enc.byteLength
}
async function readTable(doctype) {
  if (memory.has(doctype)) return memory.get(doctype)
  try {
    const enc = await tx('readonly', (s) => s.get(tableKey(doctype)))
    if (!enc) return null
    const table = JSON.parse(await gunzip((await decryptBytes(enc)).buffer))
    memory.set(doctype, table)
    return table
  } catch {
    return null
  }
}

async function writeInfo(info) {
  const enc = await encryptJson(info)
  await tx('readwrite', (s) => s.put(enc, INFO))
  storeInfo.value = info
}

// Read the summary of what is stored (so the screens can say so). Another person's copy is never
// shown to, or used by, someone else who signs in on the same phone.
export async function loadStoreInfo(user) {
  try {
    const enc = await tx('readonly', (s) => s.get(INFO))
    const info = enc ? await decryptJson(enc) : null
    if (info && user && info.user !== user) {
      await removeStore()
      return null
    }
    storeInfo.value = info
    appIconDataUrl.value = (await tx('readonly', (s) => s.get(ICON))) || null
    return info
  } catch {
    storeInfo.value = null
    return null
  }
}

export async function removeStore() {
  memory.clear()
  storeInfo.value = null
  appIconDataUrl.value = null
  await new Promise((resolve) => {
    const request = indexedDB.deleteDatabase(DB_NAME)
    request.onsuccess = request.onerror = request.onblocked = () => resolve()
  })
}

export async function hasStore() {
  try {
    return !!(await tx('readonly', (s) => s.count(INFO)))
  } catch {
    return false
  }
}

const tick = (ms = 250) => new Promise((r) => setTimeout(r, ms))
const setStep = (step, percent) => (storeState.value = { ...storeState.value, step, percent })

// Fetch (only what changed since the last time) -> merge -> compress + encrypt -> store.
// The pace of the steps is only so the progress is visible.
export async function downloadOffline(user) {
  if (storeState.value.downloading) return
  storeState.value = { downloading: true, step: 'Collecting the data…', percent: 10, error: null }
  try {
    const previous = storeInfo.value && storeInfo.value.user === user ? storeInfo.value : null
    const res = await call('janadhikara.offline.get_offline_data', previous ? { since: previous.generated } : {})
    const data = res?.message ?? res
    setStep('Saving on this device…', 45)
    await tick()
    const counts = {}
    const children = []
    let bytes = 0
    for (const [doctype, incoming] of Object.entries(data.doctypes)) {
      const before = previous ? await readTable(doctype) : null
      const merged = new Map((before?.docs || []).map((d) => [d.name, d]))
      for (const doc of incoming.docs) merged.set(doc.name, doc)
      // drop what the server no longer lets this person read (deleted, or moved to someone else)
      const keep = new Set(incoming.names)
      for (const name of [...merged.keys()]) if (!keep.has(name)) merged.delete(name)
      const docs = [...merged.values()]
      bytes += await writeTable(doctype, { title_field: incoming.title_field, istable: incoming.istable, docs })
      counts[doctype] = docs.length
      if (incoming.istable) children.push(doctype)
    }
    // a doctype this person can no longer read is dropped too
    for (const doctype of Object.keys(storeInfo.value?.counts || {})) {
      if (!(doctype in counts)) {
        await tx('readwrite', (s) => s.delete(tableKey(doctype)))
        memory.delete(doctype)
      }
    }
    await writeInfo({ user: data.user, generated: data.generated, bytes, counts, children, metaDoctypes: data.meta_doctypes || [] })
    await cacheAppIcon()
    setStep('Saving form layouts…', 85)
    await warmAppCaches(data.meta_doctypes || [])
    setStep('Done', 100)
    await tick(500)
  } catch (e) {
    storeState.value = { ...storeState.value, error: e?.messages?.[0] || e?.message || 'Could not download the data' }
    return
  }
  storeState.value = { downloading: false, step: '', percent: 0, error: null }
}

// ---- Reading ---------------------------------------------------------------------------------------
export const getTable = readTable // { title_field, istable, docs } | null
export async function getDocs(doctype) {
  return (await readTable(doctype))?.docs || null
}
export async function getDoc(doctype, name) {
  return (await getDocs(doctype))?.find((d) => d.name === name) || null
}

// Rows narrowed by simple equality filters (the { fieldname: value } filters the Link picker sends).
export async function localRows(doctype, filters = {}) {
  const docs = await getDocs(doctype)
  if (!docs) return null
  const wanted = Object.entries(filters || {}).filter(([, v]) => v != null && v !== '' && !Array.isArray(v))
  return docs.filter((row) => wanted.every(([field, value]) => String(row[field] ?? '') === String(value)))
}

// A record's title for display (the Link picker's label), or undefined.
export async function localTitle(doctype, name) {
  const table = await readTable(doctype)
  const doc = table?.docs.find((d) => String(d.name) === String(name))
  return doc ? doc[table.title_field || 'name'] : undefined
}

// After an offline edit uploads: keep the phone's copy in step with what the server now holds.
export async function putLocalDoc(doctype, doc) {
  const table = await readTable(doctype)
  if (!table || !doc?.name) return
  const docs = table.docs.filter((d) => d.name !== doc.name)
  await writeTable(doctype, { ...table, docs: [doc, ...docs] })
}

// The app's own pages ask the server for a few things (the form layout of each doctype, the
// module list, settings) with plain GET requests, which the service worker keeps for offline
// use once they have been made. Make them now - for this app's own doctypes only - so forms
// open offline even if they were never opened online.
const WARM_METHODS = [
  'janadhikara.api.get_app_modules',
  'janadhikara.api.get_app_branding',
  'janadhikara.api.get_current_user_context',
  'janadhikara.api.get_settings_entries',
  'janadhikara.api.get_field_function_rules',
  'janadhikara.api.get_field_function_registry',
]
async function warmAppCaches(doctypes) {
  const worker = (await navigator.serviceWorker?.getRegistration('/janadhikara/'))?.active
  worker?.postMessage('janadhikara-cache-shell')
  const urls = [
    ...WARM_METHODS.map((m) => `/api/v2/method/${m}?`), // the app's own requests end in "?" when they have no parameters
    ...doctypes.map((d) => `/api/v2/doctype/${encodeURIComponent(d)}/meta`),
  ]
  // A few at a time; one that fails (no permission, say) never stops the rest.
  for (let i = 0; i < urls.length; i += 6) {
    await Promise.all(urls.slice(i, i + 6).map((url) => fetch(url, { credentials: 'include' }).catch(() => null)))
  }
  // The worker saves each reply a moment after it arrives: give it a moment, then ask once more for any that are missing.
  await new Promise((r) => setTimeout(r, 800))
  try {
    const have = new Set((await (await caches.open('janadhikara-api-reads')).keys()).map((r) => new URL(r.url).pathname))
    for (const url of urls.filter((u) => !have.has(u.replace(/\?$/, '')))) await fetch(url, { credentials: 'include' }).catch(() => null)
  } catch {
    // the readiness list shows what is still missing
  }
}

// Only the app icon is kept as an image - small, and made on the device from the logo.
async function cacheAppIcon() {
  try {
    const res = await call('janadhikara.api.get_app_branding')
    const branding = res?.message ?? res
    const url = branding?.app_logo || branding?.app_logo_dark
    if (!url) return
    const bitmap = await createImageBitmap(await (await fetch(url)).blob())
    const size = 128
    const canvas = Object.assign(document.createElement('canvas'), { width: size, height: size })
    const scale = Math.min(size / bitmap.width, size / bitmap.height)
    canvas.getContext('2d').drawImage(bitmap, (size - bitmap.width * scale) / 2, (size - bitmap.height * scale) / 2, bitmap.width * scale, bitmap.height * scale)
    const dataUrl = canvas.toDataURL('image/png')
    await tx('readwrite', (store) => store.put(dataUrl, ICON))
    appIconDataUrl.value = dataUrl
  } catch {
    // the default Janadhikara icon is built into the app, so nothing is lost
  }
}

// ---- "Is this device ready to work offline?" ------------------------------------------
// Each thing the app needs to start and work without a connection, and whether it is in place.
export async function checkOfflineReadiness() {
  const checks = []
  const add = (key, label, ok, detail) => checks.push({ key, label, ok, detail })

  // 1. The service worker that serves the app with no connection.
  let worker = null
  try {
    const registration = await navigator.serviceWorker?.getRegistration('/janadhikara/')
    worker = registration?.active || null
    add('worker', 'Offline engine installed', !!worker, worker ? 'Active' : 'Not active yet - reload the app once, and accept the update prompt if one appears.')
  } catch {
    add('worker', 'Offline engine installed', false, 'This browser does not allow it.')
  }

  // 1b. The app's own code saved for every screen (older versions saved it under the wrong address, so
  // a screen not opened before failed to load offline with "Failed to fetch").
  try {
    const names = (await caches.keys()).filter((n) => n.startsWith('workbox-precache'))
    let found = 0
    for (const name of names) {
      const keys = await (await caches.open(name)).keys()
      found += keys.filter((r) => new URL(r.url).pathname.startsWith('/assets/janadhikara/frontend/assets/')).length
    }
    add('code', 'App screens saved', found > 0, found > 0 ? `${found} files` : 'Update the app while online: accept the "new version" prompt, or close and reopen the app.')
  } catch {
    add('code', 'App screens saved', false, 'Open the app once with internet.')
  }

  // 2. The saved copy of the app page (served for any address when offline).
  try {
    const shell = await (await caches.open('janadhikara-shell')).match('/janadhikara/__shell')
    add('shell', 'App page saved', !!shell, shell ? 'Ready' : 'Open the app once with internet.')
  } catch {
    add('shell', 'App page saved', false, 'Open the app once with internet.')
  }

  // 3. The module list (Home screen and sidebar).
  const modules = (await import('@/data/localSnapshot')).readSnapshot('app-modules')
  add('modules', 'Modules saved', Array.isArray(modules) && modules.length > 0, modules?.length ? `${modules.length} modules` : 'Open Home once with internet.')

  // 4. Form layouts for this app's own doctypes.
  try {
    const wanted = storeInfo.value?.metaDoctypes || []
    const keys = await (await caches.open('janadhikara-api-reads')).keys()
    const metaUrls = new Set(keys.map((r) => new URL(r.url).pathname))
    const have = wanted.filter((d) => metaUrls.has(`/api/v2/doctype/${encodeURIComponent(d)}/meta`))
    const known = wanted.length > 0
    add('layouts', 'Form layouts saved', known && have.length === wanted.length, known ? `${have.length} of ${wanted.length}` : 'Press Download on this page.')
  } catch {
    add('layouts', 'Form layouts saved', false, 'Press Download on this page.')
  }

  // 5. The records for dropdowns.
  add('pack', 'Records and dropdown data saved', !!storeInfo.value, storeInfo.value ? 'Ready' : 'Press Download on this page.')
  return checks
}

