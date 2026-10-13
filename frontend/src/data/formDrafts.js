// Unsaved forms kept on this device, so a phone switching off, a closed window or a hung app does not lose what was typed.
//
// A draft is written every 30 seconds while a form has unsaved changes (and when the page is hidden), encrypted with the
// same device key as the offline records, and only for the user who typed it. Nothing is sent to the server: the record is
// created only when the worker presses Save. A draft is deleted once the record is saved, and after a day.
import { encryptJson, decryptJson } from '@/data/deviceCrypto'
import { session } from '@/data/session'

const DB_NAME = 'janadhikara-drafts'
const STORE = 'drafts'
const MAX_AGE_MS = 24 * 60 * 60 * 1000

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
