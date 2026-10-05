// Shows a linked record by its title (the target doctype's title_field -
// e.g. a Settlement's name, a worker's name) instead of its record ID,
// wherever a Link value is displayed read-only: list cells, mobile cards,
// child-table rows. (The Link field control itself already does this.)
//
// Titles are fetched in batches per doctype (janadhikara.api.get_link_titles)
// and cached for the page's lifetime in a reactive map, so any render that
// reads linkTitle() updates by itself once the batch lands. Until then - or
// when a record has no title, or the user can't read it - the ID is shown.
import { reactive } from 'vue'
import { call } from 'frappe-ui'
import { localTitle } from '@/data/offlinePack'

const titles = reactive({})
const keyOf = (doctype, name) => `${doctype}\u0000${name}`

export function linkTitle(doctype, name) {
  if (!doctype || !name) return name
  return titles[keyOf(doctype, name)] || name
}

export function isTitledLink(field) {
  // Users keep their own hover-card display, so they're left alone.
  return field?.fieldtype === 'Link' && !!field.options && field.options !== 'User'
}

async function ensureLinkTitles(doctype, names) {
  const missing = [...new Set(names.filter((n) => typeof n === 'string' && n && !(keyOf(doctype, n) in titles)))]
  if (!missing.length) return
  // Mark as "asked" (falls back to the ID) so concurrent renders don't ask twice.
  missing.forEach((n) => (titles[keyOf(doctype, n)] = ''))
  try {
    const res = await call('janadhikara.api.get_link_titles', { doctype, names: JSON.stringify(missing) })
    const map = (res && !Array.isArray(res) && (res.message ?? res)) || {}
    missing.forEach((n) => (titles[keyOf(doctype, n)] = map[n] || ''))
  } catch {
    // No connection: take the titles from the copy of the data kept on this device.
    for (const n of missing) {
      const title = await localTitle(doctype, n)
      if (title) titles[keyOf(doctype, n)] = title
    }
  }
}

// Collects every Link value in `rows` for the given fields and fetches their
// titles (one request per linked doctype).
export function ensureTitlesForRows(rows, fields) {
  const byDoctype = {}
  for (const field of fields) {
    if (!isTitledLink(field)) continue
    for (const row of rows || []) {
      const value = row?.[field.fieldname]
      if (value) (byDoctype[field.options] ||= []).push(value)
    }
  }
  return Promise.all(Object.entries(byDoctype).map(([doctype, names]) => ensureLinkTitles(doctype, names)))
}
