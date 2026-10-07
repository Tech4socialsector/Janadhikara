// Records saved on this device while there was no connection, waiting to be uploaded.
//
// Kept in IndexedDB (a form with child tables can be larger than localStorage
// likes). The queue is mirrored in a reactive list so the Sync Data page, the
// sidebar badge and the Home tile all update by themselves. Once an item has been
// uploaded it is deleted; when the queue is empty the whole database is removed, so
// nothing is left behind on the device.
import { computed, ref } from 'vue'
import { call } from 'frappe-ui'
import { encryptJson, decryptJson } from '@/data/deviceCrypto'
import { session } from '@/data/session'

const DB_NAME = 'janadhikara-offline'
const STORE = 'queue'

export const queue = ref([]) // newest last
let otherUsersCount = 0 // records saved here by someone else: kept, never shown or uploaded for this user
export const pendingCount = computed(() => queue.value.length)
export const syncState = ref({ running: false, done: 0, total: 0 })

// ---- IndexedDB plumbing ------------------------------------------------------
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'id' })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function run(mode, work) {
  const db = await openDb()
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode)
      const result = work(tx.objectStore(STORE))
      tx.oncomplete = () => resolve(result?.result ?? result)
      tx.onerror = () => reject(tx.error)
    })
  } finally {
    db.close()
  }
}

export async function loadQueue() {
  try {
    const stored = await new Promise(async (resolve, reject) => {
      const db = await openDb()
      const request = db.transaction(STORE, 'readonly').objectStore(STORE).getAll()
      request.onsuccess = () => {
        db.close()
        resolve(request.result || [])
      }
      request.onerror = () => reject(request.error)
    })
    const items = []
    otherUsersCount = 0
    for (const row of stored.sort((a, b) => a.createdAt - b.createdAt)) {
      try {
        const item = await decryptJson(row.enc)
        // A record belongs to the person who saved it: on a shared phone it is never shown to,
        // or uploaded as, someone else.
        if (item.user && session.user && item.user !== session.user) {
          otherUsersCount++
          continue
        }
        items.push({ ...item, status: item.status === 'syncing' ? 'pending' : item.status })
      } catch {
        // unreadable (its key is gone) - nothing to show
      }
    }
    queue.value = items
  } catch {
    queue.value = []
  }
}

// Stored encrypted; only the id and the saved time (for ordering) are left readable.
async function put(item) {
  const enc = await encryptJson(JSON.parse(JSON.stringify(item)))
  await run('readwrite', (store) => store.put({ id: item.id, createdAt: item.createdAt, enc }))
}

async function dropDatabaseIfEmpty() {
  if (queue.value.length || otherUsersCount) return
  try {
    await new Promise((resolve) => {
      const request = indexedDB.deleteDatabase(DB_NAME)
      request.onsuccess = request.onerror = request.onblocked = () => resolve()
    })
  } catch {
    // nothing to clean
  }
}

// ---- Queue operations ------------------------------------------------------------
const clean = (value) => JSON.parse(JSON.stringify(value, (key, v) => (key.startsWith('__') ? undefined : v)))

export async function enqueueRecord({ doctype, name, action, doc, title }) {
  const item = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    doctype,
    name: name || null,
    action, // 'insert' | 'update'
    doc: clean({ ...doc, doctype }),
    title: title || name || doctype,
    createdAt: Date.now(),
    user: session.user || null,
    status: 'pending',
    error: null,
  }
  // The same existing record saved twice offline keeps only the latest edit.
  if (action === 'update') {
    const previous = queue.value.find((i) => i.action === 'update' && i.doctype === doctype && i.name === name)
    if (previous) await discard(previous.id, { keepDb: true })
  }
  await put(item)
  queue.value = [...queue.value, item]
  return item
}

// Edit a record that is still waiting: replace its saved data, keep its place in the queue.
export async function updateRecord(id, { doc, title }) {
  const current = queue.value.find((i) => i.id === id)
  if (!current) return null
  const item = { ...current, doc: clean({ ...doc, doctype: current.doctype }), title: title || current.title, status: 'pending', error: null }
  await put(item)
  queue.value = queue.value.map((i) => (i.id === id ? item : i))
  return item
}

export async function discard(id, { keepDb = false } = {}) {
  await run('readwrite', (store) => store.delete(id))
  queue.value = queue.value.filter((i) => i.id !== id)
  if (!keepDb) await dropDatabaseIfEmpty()
}

function setStatus(id, patch) {
  queue.value = queue.value.map((i) => (i.id === id ? { ...i, ...patch } : i))
}

const errorText = (e) => {
  const raw = e?.messages?.[0] || e?.message || e?.exception || 'Could not upload'
  return String(raw).replace(/<[^>]*>/g, '').slice(0, 300)
}

export const isNetworkError = (e) =>
  !navigator.onLine || e instanceof TypeError || /failed to fetch|network|load failed/i.test(String(e?.message || e))

// ---- Upload ---------------------------------------------------------------------------
async function uploadOne(item) {
  if (item.action === 'insert') {
    await call('frappe.client.insert', { doc: item.doc })
  } else {
    await call('frappe.client.save', { doc: { ...item.doc, name: item.name } })
  }
}

// Uploads everything in order. An item that fails (a validation error, a record changed
// by someone else meanwhile) stays in the list with its message; the rest carry on.
// Pass `ids` to upload just those records (the ones ticked on the Sync Data page).
export async function syncAll(ids = null) {
  if (syncState.value.running) return { uploaded: 0, failed: 0 }
  const items = queue.value.filter((i) => i.status !== 'done' && (!ids || ids.includes(i.id)))
  syncState.value = { running: true, done: 0, total: items.length }
  let uploaded = 0
  let failed = 0
  for (const item of items) {
    setStatus(item.id, { status: 'syncing', error: null })
    try {
      await uploadOne(item)
      setStatus(item.id, { status: 'done' })
      await new Promise((r) => setTimeout(r, 450)) // let the tick show
      await discard(item.id, { keepDb: true })
      uploaded++
    } catch (e) {
      const offline = isNetworkError(e)
      setStatus(item.id, { status: offline ? 'pending' : 'failed', error: offline ? 'No connection' : errorText(e) })
      if (offline) {
        failed += items.length - uploaded
        break
      }
      await put({ ...item, status: 'failed', error: errorText(e) })
      failed++
    }
    syncState.value = { ...syncState.value, done: syncState.value.done + 1 }
  }
  await dropDatabaseIfEmpty()
  syncState.value = { ...syncState.value, running: false }
  return { uploaded, failed }
}

// ---- Download a copy ----------------------------------------------------------------------
function save(filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const stamp = () => new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')

export function downloadJson() {
  const data = queue.value.map(({ doctype, name, action, doc, createdAt }) => ({
    doctype,
    action,
    name,
    saved_on: new Date(createdAt).toISOString(),
    data: doc,
  }))
  save(`janadhikara-unsynced-${stamp()}.json`, JSON.stringify(data, null, 2), 'application/json')
}

// One CSV with a column per field seen (child tables as JSON text).
export function downloadCsv() {
  const rows = queue.value.map((i) => ({ doctype: i.doctype, action: i.action, record: i.name || '', saved_on: new Date(i.createdAt).toISOString(), ...i.doc }))
  const columns = [...new Set(rows.flatMap((r) => Object.keys(r)))]
  const cell = (v) => {
    const text = v == null ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v)
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const lines = [columns.join(','), ...rows.map((r) => columns.map((c) => cell(r[c])).join(','))]
  save(`janadhikara-unsynced-${stamp()}.csv`, lines.join('\n'), 'text/csv')
}

export const queueReady = loadQueue()
