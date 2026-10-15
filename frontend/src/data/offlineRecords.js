// "Download my records": the signed-in person's own Settlements, Household and Individual
// Profiles (child tables included, no files or photos) kept encrypted on this phone so they can
// be opened and edited with no connection. Started only by the button on Sync Data - never by
// a timer or by the connection coming back. Kept per user; removed on logout, on "Remove from
// this phone", or when someone else signs in here.
import { ref, shallowRef } from 'vue'
import { call } from 'frappe-ui'
import { encryptJson, decryptJson } from '@/data/deviceCrypto'

const DB_NAME = 'janadhikara-records'
const STORE = 'records'
const KEY = 'main'

export const recordsInfo = ref(null) // { user, generated, counts: { Doctype: n } }
export const recordsState = ref({ downloading: false, error: null })
// { user, generated, records: { Doctype: { name: doc } } }
const memory = shallowRef(null)

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

const countsOf = (records) => Object.fromEntries(Object.entries(records).map(([d, rows]) => [d, Object.keys(rows).length]))

async function persist(data) {
  const enc = await encryptJson(data)
  await tx('readwrite', (s) => s.put(enc, KEY))
  memory.value = data
  recordsInfo.value = { user: data.user, generated: data.generated, counts: countsOf(data.records) }
}

export async function loadRecords(user) {
  if (memory.value) return memory.value
  try {
    const enc = await tx('readonly', (s) => s.get(KEY))
    if (!enc) return null
    const data = await decryptJson(enc)
    // Another person signed in here since: their copy is not this person's to see.
    if (user && data.user !== user) {
      await removeRecords()
      return null
    }
    memory.value = data
    recordsInfo.value = { user: data.user, generated: data.generated, counts: countsOf(data.records) }
    return data
  } catch {
    return null
  }
}

export async function removeRecords() {
  memory.value = null
  recordsInfo.value = null
  await new Promise((resolve) => {
    const request = indexedDB.deleteDatabase(DB_NAME)
    request.onsuccess = request.onerror = request.onblocked = () => resolve()
  })
}

export async function hasStoredRecords() {
  try {
    return !!(await tx('readonly', (s) => s.count(KEY)))
  } catch {
    return false
  }
}

// Fetch what changed since the last download (everything the first time) and merge it in.
export async function downloadRecords(user) {
  if (recordsState.value.downloading) return
  recordsState.value = { downloading: true, error: null }
  try {
    const previous = await loadRecords(user)
    const since = previous?.generatedServer || null
    const res = await call('janadhikara.offline.get_offline_records', since ? { since } : {})
    const records = previous ? JSON.parse(JSON.stringify(previous.records)) : {}
    for (const [doctype, docs] of Object.entries(res.records || {})) {
      records[doctype] = records[doctype] || {}
      for (const doc of docs) records[doctype][doc.name] = doc
    }
    // Drop what the server no longer lets this person read (deleted, or moved to someone else).
    for (const [doctype, names] of Object.entries(res.names || {})) {
      const keep = new Set(names)
      for (const name of Object.keys(records[doctype] || {})) if (!keep.has(name)) delete records[doctype][name]
    }
    await persist({ user: res.user, generated: res.generated, generatedServer: res.generated, records })
  } catch (e) {
    recordsState.value = { downloading: false, error: e?.messages?.[0] || e?.message || 'Could not download' }
    throw e
  }
  recordsState.value = { downloading: false, error: null }
}

export async function getLocalRecord(doctype, name, user) {
  const data = await loadRecords(user)
  const doc = data?.records?.[doctype]?.[name]
  return doc ? JSON.parse(JSON.stringify(doc)) : null
}

export async function localRecordList(doctype, user) {
  const data = await loadRecords(user)
  return Object.values(data?.records?.[doctype] || {})
}

// After an offline edit uploads, or the person keeps the server's version: refresh that one record.
export async function putLocalRecord(doctype, doc) {
  const data = memory.value || (await loadRecords())
  if (!data || !doc?.name) return
  data.records[doctype] = data.records[doctype] || {}
  data.records[doctype][doc.name] = doc
  await persist({ ...data })
}

export async function dropLocalRecord(doctype, name) {
  const data = memory.value || (await loadRecords())
  if (!data?.records?.[doctype]) return
  delete data.records[doctype][name]
  await persist({ ...data })
}
