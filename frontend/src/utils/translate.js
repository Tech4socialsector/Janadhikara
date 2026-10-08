import { shallowRef, watch } from 'vue'
import { call } from 'frappe-ui'
import { appLanguage } from '@/data/language'

// The app's translations live in Frappe's Translation doctype (contexts starting "janadhikara:"), where they can
// be edited in Desk. They are fetched for the chosen language and kept on this device, so they work offline.
// Saved answers stay in English: only what is shown changes.
const EMPTY = { ui: {}, heading: {}, option: {}, help: {}, dpdp: {}, fields: {} }
const cacheKey = (language) => `janadhikara-translations-${language}`
const store = shallowRef(EMPTY)

function readCache(language) {
  try {
    return JSON.parse(localStorage.getItem(cacheKey(language)) || 'null')
  } catch {
    return null
  }
}

watch(
  appLanguage,
  async (language) => {
    if (!language || language === 'en') {
      store.value = EMPTY
      return
    }
    store.value = readCache(language) || EMPTY
    try {
      const data = await call('janadhikara.translations.get_app_translations', { language })
      if (appLanguage.value !== language) return
      store.value = { ...EMPTY, ...data }
      try {
        localStorage.setItem(cacheKey(language), JSON.stringify(data))
      } catch {
        // not kept on this device
      }
    } catch {
      // offline and nothing kept yet: English
    }
  },
  { immediate: true },
)

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
