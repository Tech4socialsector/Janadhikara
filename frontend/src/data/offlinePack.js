// A compressed copy of the reference data (masters, linked records and the app's own
// records - field data only, no files or images) kept on this device so Link pickers and
// look-ups still work with no connection.
//
// The server builds it (janadhikara.offline.get_offline_pack, only what the user may
// read); here it is gzip-compressed and stored in IndexedDB. It is read back into memory
// the first time something needs it.
import { ref, shallowRef } from 'vue'
import { call } from 'frappe-ui'
import { encryptBytes, decryptBytes, encryptJson, decryptJson } from '@/data/deviceCrypto'

const DB_NAME = 'janadhikara-pack'
const STORE = 'pack'
const KEY = 'main'

export const packInfo = ref(null) // { generated, bytes, counts: { Doctype: rows }, user }
export const packState = ref({ downloading: false, step: '', percent: 0, error: null })
const memory = shallowRef(null) // the decompressed pack
// The app's own icon, kept so the header still shows it with no connection (the only image stored).
export const appIconDataUrl = ref(null)

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

async function gzip(text) {
  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'))
  return new Response(stream).arrayBuffer()
}
async function gunzip(buffer) {
  const stream = new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))
  return new Response(stream).text()
}

const tick = (ms = 250) => new Promise((r) => setTimeout(r, ms))
const setStep = (step, percent) => (packState.value = { ...packState.value, step, percent })

// Fetch -> compress -> store. The pace of the steps is only so the progress is visible.
export async function downloadPack() {
  if (packState.value.downloading) return
  packState.value = { downloading: true, step: 'Collecting the data…', percent: 10, error: null }
  try {
    const res = await call('janadhikara.offline.get_offline_pack')
    const pack = res?.message ?? res
    setStep('Compressing…', 55)
    await tick()
    const compressed = await gzip(JSON.stringify(pack))
    setStep('Saving on this device…', 80)
    await tick()
    const counts = Object.fromEntries(Object.entries(pack.doctypes).map(([d, v]) => [d, v.rows.length]))
    const info = { generated: pack.generated, user: pack.user, bytes: compressed.byteLength, counts, metaDoctypes: pack.meta_doctypes || [] }
    const encInfo = await encryptJson(info)
    const encData = await encryptBytes(new Uint8Array(compressed))
    await tx('readwrite', (store) =>
      store.put({ info: encInfo, data: encData }, KEY),
    )
    memory.value = pack
    packInfo.value = info
    await cacheAppIcon()
    setStep('Saving form layouts…', 90)
    await warmAppCaches(pack.meta_doctypes || [])
    setStep('Done', 100)
    await tick(500)
  } catch (e) {
    packState.value = { ...packState.value, error: e?.messages?.[0] || e?.message || 'Could not download the data' }
    return
  }
  packState.value = { downloading: false, step: '', percent: 0, error: null }
}

export async function removePack() {
  await new Promise((resolve) => {
    memory.value = null
    packInfo.value = null
    appIconDataUrl.value = null
    const request = indexedDB.deleteDatabase(DB_NAME)
    request.onsuccess = request.onerror = request.onblocked = () => resolve()
  })
}

export async function loadPackInfo() {
  try {
    const record = await tx('readonly', (store) => store.get(KEY))
    packInfo.value = record ? await decryptJson(record.info) : null
    appIconDataUrl.value = (await tx('readonly', (store) => store.get('icon'))) || null
  } catch {
    packInfo.value = null
  }
}

// The whole pack, decompressed once and kept in memory.
export async function getPack() {
  if (memory.value) return memory.value
  try {
    const record = await tx('readonly', (store) => store.get(KEY))
    if (!record) return null
    memory.value = JSON.parse(await gunzip((await decryptBytes(record.data)).buffer))
    return memory.value
  } catch {
    return null
  }
}

// ---- Look-ups used when the server can't be reached --------------------------------
const toObjects = (table) => table.rows.map((row) => Object.fromEntries(table.columns.map((c, i) => [c, row[i]])))

// Rows of a doctype as { fieldname: value } objects, narrowed by simple equality filters
// (the same { fieldname: value } filters the Link picker sends to the server).
export async function localRows(doctype, filters = {}) {
  const table = (await getPack())?.doctypes?.[doctype]
  if (!table) return null
  const wanted = Object.entries(filters || {}).filter(([, v]) => v != null && v !== '' && !Array.isArray(v))
  return toObjects(table).filter((row) => wanted.every(([field, value]) => String(row[field] ?? '') === String(value)))
}

// Options for a Link picker: [{ label, value }].
export async function localLinkOptions(doctype, filters = {}) {
  const pack = await getPack()
  const table = pack?.doctypes?.[doctype]
  if (!table) return null
  const title = table.title_field || 'name'
  return (await localRows(doctype, filters)).map((row) => ({ label: row[title] || row.name, value: String(row.name) }))
}

// A record's title for display (the Link picker's label), or undefined.
export async function localTitle(doctype, name) {
  const table = (await getPack())?.doctypes?.[doctype]
  if (!table) return undefined
  const titleIndex = table.columns.indexOf(table.title_field || 'name')
  const row = table.rows.find((r) => String(r[0]) === String(name))
  return row ? row[titleIndex] : undefined
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
  const urls = [
    ...WARM_METHODS.map((m) => `/api/v2/method/${m}`),
    ...doctypes.map((d) => `/api/v2/doctype/${encodeURIComponent(d)}/meta`),
  ]
  // A few at a time; one that fails (no permission, say) never stops the rest.
  for (let i = 0; i < urls.length; i += 6) {
    await Promise.all(urls.slice(i, i + 6).map((url) => fetch(url, { credentials: 'include' }).catch(() => null)))
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
    await tx('readwrite', (store) => store.put(dataUrl, 'icon'))
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
    const wanted = packInfo.value?.metaDoctypes || []
    const keys = await (await caches.open('janadhikara-api-reads')).keys()
    const metaUrls = new Set(keys.map((r) => new URL(r.url).pathname))
    const have = wanted.filter((d) => metaUrls.has(`/api/v2/doctype/${encodeURIComponent(d)}/meta`))
    const known = wanted.length > 0
    add('layouts', 'Form layouts saved', known && have.length === wanted.length, known ? `${have.length} of ${wanted.length}` : 'Press Download on this page.')
  } catch {
    add('layouts', 'Form layouts saved', false, 'Press Download on this page.')
  }

  // 5. The records for dropdowns.
  add('pack', 'Dropdown data saved', !!packInfo.value, packInfo.value ? 'Ready' : 'Press Download on this page.')
  return checks
}

export const packReady = loadPackInfo()
