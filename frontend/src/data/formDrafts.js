// Unsaved forms kept safe while they are being filled in, so a phone switching off, a closed window, a signed-out session
// or a hung app does not lose what was typed.
//
// Two copies, both private to the user who typed it: one on this device (encrypted with the same device key as the offline
// records; written instantly and works without a network) and one on the server (janadhikara.drafts; follows the user to
// another phone or browser). The record itself is created only when the worker presses Save. A draft is deleted once the
// record is saved or discarded, and after 7 days.
import { encryptJson, decryptJson } from '@/data/deviceCrypto'
import { session } from '@/data/session'
import { call } from 'frappe-ui'

const DB_NAME = 'janadhikara-drafts'
const STORE = 'drafts'
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000

export const draftKey = (doctype, name) => `${session.user || ''}|${doctype}|${name || 'new'}`

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'key' })
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

const clean = (value) => JSON.parse(JSON.stringify(value, (key, v) => (key.startsWith('__') ? undefined : v)))

export async function saveDraft(key, values) {
  try {
    const enc = await encryptJson(clean(values))
    const savedAt = Date.now()
    await run('readwrite', (store) => store.put({ key, savedAt, enc }))
    return savedAt
  } catch {
    return null // storage full or blocked: the form still works
  }
}

export async function loadDraft(key) {
  try {
    const row = await run('readonly', (store) => store.get(key))
    if (!row) return null
    if (Date.now() - row.savedAt > MAX_AGE_MS) {
      await deleteDraft(key)
      return null
    }
    return { values: await decryptJson(row.enc), savedAt: row.savedAt }
  } catch {
    return null
  }
}

export async function deleteDraft(key) {
  try {
    await run('readwrite', (store) => store.delete(key))
  } catch {
    // nothing to delete
  }
}

// --- The copy on the server ----------------------------------------------------------------------------------------
// Best effort: a failure (offline, signed out, not permitted) leaves the device copy, which is always written first.
const serverArgs = (doctype, name) => ({ doctype, name: name || '' })

export async function saveServerDraft(doctype, name, values) {
  try {
    await call('janadhikara.drafts.save_draft', { ...serverArgs(doctype, name), data: JSON.stringify(clean(values)) })
    return Date.now()
  } catch {
    return null
  }
}

export async function loadServerDraft(doctype, name) {
  try {
    const res = await call('janadhikara.drafts.get_draft', serverArgs(doctype, name))
    const draft = res?.message ?? res
    if (!draft?.data) return null
    // the server stamps `modified` in its own clock: read as a UTC-less local time, only for showing "saved at"
    return { values: draft.data, savedAt: new Date(String(draft.modified).replace(' ', 'T')).getTime() || Date.now() }
  } catch {
    return null
  }
}

export async function deleteServerDraft(doctype, name) {
  try {
    await call('janadhikara.drafts.delete_draft', serverArgs(doctype, name))
  } catch {
    // nothing to delete, or no connection: the daily clean-up removes it
  }
}
