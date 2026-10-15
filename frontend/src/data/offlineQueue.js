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

// A record made offline has no real name yet: it carries a temporary one, which other offline
// records (an individual of an offline household) can point to. When the record uploads, the
// temporary name is swapped for the real one everywhere it was used.
export const TEMP_PREFIX = 'OFFLINE-'
export const isTempName = (v) => typeof v === 'string' && v.startsWith(TEMP_PREFIX)

// `base` is the server's copy the edit started from (existing records only): it lets the upload
// send just the fields that changed and notice if someone else changed the same ones meanwhile.
export async function enqueueRecord({ doctype, name, action, doc, title, base = null }) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  const item = {
    id,
    doctype,
    name: name || null,
    tempName: action === 'insert' ? `${TEMP_PREFIX}${id}` : null,
    action, // 'insert' | 'update'
    base: action === 'update' ? clean(base || {}) : null,
    baseModified: action === 'update' ? base?.modified || doc?.modified || null : null,
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
    if (previous) {
      // keep the copy the first edit started from, so the conflict check is against what the server had then
      item.base = previous.base || item.base
      item.baseModified = previous.baseModified || item.baseModified
      await discard(previous.id, { keepDb: true })
    }
  }
  await put(item)
  queue.value = [...queue.value, item]
  return item
}

// Edit a record that is still waiting: replace its saved data, keep its place in the queue.
export async function updateRecord(id, { doc, title }) {
  const current = queue.value.find((i) => i.id === id)
  if (!current) return null
  const item = { ...current, doc: clean({ ...doc, doctype: current.doctype }), title: title || current.title, status: 'pending', error: null, conflict: null, waitingOn: null }
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
// Every upload carries the item's own id. If the connection drops after the server saved the
// record but before the reply arrived, sending it again returns the first result - no duplicate.
const META_KEYS = new Set(['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus', 'idx', 'parent', 'parentfield', 'parenttype', 'doctype'])
const norm = (v) => {
  if (Array.isArray(v)) return v.map(norm)
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).filter(([k]) => !META_KEYS.has(k) && !k.startsWith('__')).map(([k, x]) => [k, norm(x)]))
  if (v === '' || v === undefined) return null
  return v
}
const same = (a, b) => JSON.stringify(norm(a)) === JSON.stringify(norm(b))

// Only the fields the person changed (child tables are sent whole when any row changed).
export function changedFields(item) {
  const out = {}
  for (const [key, value] of Object.entries(item.doc)) {
    if (META_KEYS.has(key) || key.startsWith('__')) continue
    if (!same(value, item.base?.[key])) out[key] = value
  }
  return out
}

const tempRefs = (item) => {
  const found = new Set(JSON.stringify(item.doc).match(/OFFLINE-[0-9a-z-]+/g) || [])
  found.delete(item.tempName)
  return [...found]
}

// Swap a temporary name for the real one in every record still waiting.
async function replaceTempName(temp, real) {
  const swap = (v) => (v === temp ? real : Array.isArray(v) ? v.map(swap) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, swap(x)])) : v)
  for (const item of queue.value) {
    if (!JSON.stringify(item.doc).includes(temp)) continue
    const next = { ...item, doc: swap(item.doc) }
    setStatus(item.id, { doc: next.doc })
    await put(next)
  }
}

async function uploadOne(item, force = false) {
  if (item.action === 'insert') {
    const res = await call('janadhikara.offline.push_insert', { client_id: item.id, doc: item.doc })
    return { status: 'ok', name: res.name }
  }
  if (!item.base) {
    // saved before the conflict check existed: the plain save, as it was
    await call('frappe.client.save', { doc: { ...item.doc, name: item.name } })
    return { status: 'ok' }
  }
  const changes = changedFields(item)
  if (!Object.keys(changes).length) return { status: 'ok', unchanged: true }
  return call('janadhikara.offline.push_update', {
    client_id: item.id,
    doctype: item.doctype,
    name: item.name,
    changes,
    base: Object.fromEntries(Object.keys(changes).map((k) => [k, item.base[k]])),
    base_modified: item.baseModified,
    force: force ? 1 : 0,
  })
}

// One item: 'done' | 'conflict' | 'failed' | 'offline'
async function process(item, force = false) {
  setStatus(item.id, { status: 'syncing', error: null, waitingOn: null })
  try {
    const res = await uploadOne(item, force)
    if (res.status === 'conflict') {
      const next = { ...item, status: 'conflict', error: null, conflict: res.fields }
      setStatus(item.id, { status: 'conflict', error: null, conflict: res.fields })
      await put(next)
      return 'conflict'
    }
    setStatus(item.id, { status: 'done' })
    if (item.action === 'insert' && res.name) await replaceTempName(item.tempName, res.name)
    if (item.action === 'update') {
      const { putLocalDoc, getDoc } = await import('@/data/offlineStore')
      const local = await getDoc(item.doctype, item.name)
      if (local) await putLocalDoc(item.doctype, { ...local, ...item.doc, modified: res.modified || local.modified })
    }
    await new Promise((r) => setTimeout(r, 450)) // let the tick show
    await discard(item.id, { keepDb: true })
    return 'done'
  } catch (e) {
    if (isNetworkError(e)) {
      setStatus(item.id, { status: 'pending', error: 'No connection' })
      return 'offline'
    }
    setStatus(item.id, { status: 'failed', error: errorText(e) })
    await put({ ...item, status: 'failed', error: errorText(e) })
    return 'failed'
  }
}

// Uploads the records in order: one that points at another offline record (an individual of a
// household made offline) goes after it. An item that fails stays in the list with its message; the
// rest carry on. Pass `ids` to upload just those (the ones ticked on the Sync Data page).
export async function syncAll(ids = null) {
  if (syncState.value.running) return { uploaded: 0, failed: 0, conflicts: 0 }
  const items = queue.value.filter((i) => i.status !== 'done' && i.status !== 'conflict' && (!ids || ids.includes(i.id)))
  syncState.value = { running: true, done: 0, total: items.length }
  let uploaded = 0
  let failed = 0
  let conflicts = 0
  let remaining = items.map((i) => i.id)
  let offline = false
  let progress = true
  while (remaining.length && progress && !offline) {
    progress = false
    for (const id of [...remaining]) {
      const item = queue.value.find((i) => i.id === id)
      if (!item) {
        remaining = remaining.filter((r) => r !== id)
        continue
      }
      if (tempRefs(item).length) continue // its parent has not uploaded (yet)
      const outcome = await process(item)
      remaining = remaining.filter((r) => r !== id)
      progress = true
      syncState.value = { ...syncState.value, done: syncState.value.done + 1 }
      if (outcome === 'done') uploaded++
      else if (outcome === 'conflict') conflicts++
      else if (outcome === 'failed') failed++
      else {
        offline = true
        failed += remaining.length + 1
        break
      }
    }
  }
  // Left over: waiting for a record that failed, had a conflict, or was not ticked.
  for (const id of remaining) {
    const item = queue.value.find((i) => i.id === id)
    if (!item || offline) continue
    const parent = queue.value.find((p) => p.tempName && tempRefs(item).includes(p.tempName))
    setStatus(id, { status: 'pending', waitingOn: parent?.title || 'a record it belongs to', error: null })
    failed++
  }
  await dropDatabaseIfEmpty()
  syncState.value = { ...syncState.value, running: false }
  return { uploaded, failed, conflicts }
}

// The person's choice for a record someone else changed meanwhile.
//  'mine'   - upload my values over the server's
//  'server' - drop my edit and keep what the server has
export async function resolveConflict(id, choice) {
  const item = queue.value.find((i) => i.id === id)
  if (!item) return 'done'
  if (choice === 'server') {
    await discard(id)
    return 'done'
  }
  syncState.value = { running: true, done: 0, total: 1 }
  const outcome = await process(item, true)
  await dropDatabaseIfEmpty()
  syncState.value = { running: false, done: 1, total: 1 }
  return outcome
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
