// Everything kept on this device for offline work (saved records, the reference-data copy)
// is encrypted with AES-256-GCM before it is written to the browser's storage.
//
// The key is made on the device, never leaves it, and is stored as a non-extractable
// CryptoKey (the page can use it but cannot read it out). It is removed when the device's
// offline data is cleared, which also makes anything left behind unreadable.
const DB_NAME = 'janadhikara-keys'
const STORE = 'k'
const KEY_ID = 'device'
const IV_BYTES = 12

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function readKey() {
  const db = await openDb()
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction(STORE, 'readonly').objectStore(STORE).get(KEY_ID)
      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  } finally {
    db.close()
  }
}

async function writeKey(key) {
  const db = await openDb()
  try {
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite')
      tx.objectStore(STORE).put(key, KEY_ID)
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error)
    })
  } finally {
    db.close()
  }
}

let cached = null
async function getKey() {
  if (cached) return cached
  let key = await readKey()
  if (!key) {
    key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'])
    await writeKey(key)
  }
  cached = key
  return key
}

// bytes -> iv + ciphertext (one ArrayBuffer)
export async function encryptBytes(bytes) {
  const key = await getKey()
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES))
  const cipher = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, bytes))
  const out = new Uint8Array(IV_BYTES + cipher.length)
  out.set(iv)
  out.set(cipher, IV_BYTES)
  return out.buffer
}

export async function decryptBytes(buffer) {
  const key = await getKey()
  const all = new Uint8Array(buffer)
  return new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: all.slice(0, IV_BYTES) }, key, all.slice(IV_BYTES)))
}

export const encryptJson = (value) => encryptBytes(new TextEncoder().encode(JSON.stringify(value)))
export const decryptJson = async (buffer) => JSON.parse(new TextDecoder().decode(await decryptBytes(buffer)))

// Forget the key: whatever is still stored becomes unreadable noise.
export async function dropKey() {
  cached = null
  await new Promise((resolve) => {
    const request = indexedDB.deleteDatabase(DB_NAME)
    request.onsuccess = request.onerror = request.onblocked = () => resolve()
  })
}
