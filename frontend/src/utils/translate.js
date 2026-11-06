import { shallowRef, watch } from 'vue'
import { call } from 'frappe-ui'
import { appLanguage, OFFERED_LANGUAGES } from '@/data/language'
import { session } from '@/data/session'
import { online } from '@/data/connection'

// The app's translations live in Frappe's Translation doctype (contexts starting "janadhikara:"), where they can
// be edited in Desk. They are fetched for the chosen language and kept on this device, so they work offline.
// Saved answers stay in English: only what is shown changes.
const EMPTY = { ui: {}, heading: {}, option: {}, help: {}, dpdp: {}, fields: {} }
const store = shallowRef(EMPTY)

// Every offered language is kept on this device, compressed, in one small IndexedDB table - not only the one
// in use - so switching language with no connection works for all of them. (Translations are app text,
// nothing personal, so they are not encrypted.) Fetched while online, in the background, once per language.
const DB_NAME = 'janadhikara-i18n'
const STORE = 'lang'
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}
async function idb(mode, work) {
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

async function readCache(language) {
  try {
    const saved = await idb('readonly', (s) => s.get(language))
    return saved ? JSON.parse(await gunzip(saved)) : null
  } catch {
    return null
  }
}
async function writeCache(language, data) {
  try {
    const compressed = await gzip(JSON.stringify(data))
    await idb('readwrite', (s) => s.put(compressed, language))
  } catch {
    // not kept on this device
  }
}
// The earlier copy in localStorage (bigger, and only for languages already used) is no longer needed.
try {
  for (const l of OFFERED_LANGUAGES) localStorage.removeItem(`janadhikara-translations-${l}`)
} catch {
  // nothing to remove
}

const fetchLanguage = async (language) => {
  const data = await call('janadhikara.translations.get_app_translations', { language })
  // an empty answer (the server is still loading them) is not kept, so the next visit asks again
  if (Object.keys(data?.ui || {}).length) await writeCache(language, data)
  return data
}

watch(
  appLanguage,
  async (language) => {
    if (!language || language === 'en') {
      store.value = EMPTY
      return
    }
    const cached = await readCache(language)
    if (appLanguage.value !== language) return
    store.value = cached ? { ...EMPTY, ...cached } : EMPTY
    try {
      const data = await fetchLanguage(language)
      if (appLanguage.value !== language) return
      store.value = { ...EMPTY, ...data }
    } catch {
      // offline: what is kept on this device (or English when nothing is)
    }
  },
  { immediate: true },
)

// Online and signed in: make sure every offered language is on the device, so any of them can be chosen later
// with no connection. Quietly, one at a time, only the ones that are missing.
let prefetching = false
async function prefetchLanguages() {
  if (prefetching || !navigator.onLine || !session.user) return
  prefetching = true
  try {
    for (const language of OFFERED_LANGUAGES) {
      if (language === 'en' || language === appLanguage.value) continue
      if (await readCache(language)) continue
      try {
        await fetchLanguage(language)
      } catch {
        // try again next time
      }
    }
  } finally {
    prefetching = false
  }
}
watch([online, () => session.user], prefetchLanguages, { immediate: true })

// Interface text: t('Save') is the chosen language's version, or the English text when there is none.
export const t = (text) => store.value.ui[text] || text

// The DPDP consent notice: its sentences in the chosen language.
export const tn = (text) => store.value.dpdp[text] || text

// Headings the sheet does not cover: "7. Gender" -> number kept, text translated; "Please specify (Q10)" keeps its suffix.
function headingLabel(label) {
  const h = { ...store.value.ui, ...store.value.heading }
  if (!label) return null
  if (h[label]) return h[label]
  const m = /^(\s*\d+(?:\.\d+)*\s*(?:\([a-z]\))?\.?\s+)?(.*?)(\s*\(Q[\d.a-z]+\))?$/i.exec(label)
  const text = m && h[m[2]]
  return text ? `${m[1] || ''}${text}${m[3] || ''}` : null
}

// Help text the sheet does not cover: known sentences are swapped for their translation, the rest stays English.
function helpText(text) {
  const phrases = store.value.help
  if (!text || !Object.keys(phrases).length) return null
  let out = text
  for (const [en, tr] of Object.entries(phrases)) out = out.split(en).join(tr)
  return out === text ? null : out
}

// A field with its label, help text and option names in the chosen language.
// Anything without a translation stays in English. `option_labels` maps an
// option's saved (English) value to the text shown.
export function localizeField(doctype, field) {
  const entry = store.value.fields[doctype]?.[field.fieldname]
  const label = entry?.label || headingLabel(field.label) || field.label
  let options = entry?.options || null
  if (!options && field.fieldtype === 'Select') {
    const drafts = store.value.option
    if (Object.keys(drafts).length && (field.options || '').split('\n').some((o) => drafts[o.trim()])) options = drafts
  }
  const description = entry?.description || helpText(field.description) || field.description
  if (label === field.label && description === field.description && !options) return field
  return { ...field, label, description, option_labels: options }
}
