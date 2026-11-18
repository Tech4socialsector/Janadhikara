import { reactive } from 'vue'
import { call } from 'frappe-ui'

// The records a Link field can point at, for the pickers in the list filters: [{ label, value, description }], loaded once
// per doctype and shared. It is the same list the form's Link dropdowns use - every record the user may read, with
// the doctype's title shown and the record's ID under it, so records with the same title (two wards called Kapra)
// can be told apart. The entry is reactive: `options` fills in when the list arrives, `loading` is true until then.
const cache = reactive({})

export function linkOptions(doctype) {
  if (!cache[doctype]) {
    cache[doctype] = { loading: true, options: [] }
    call('janadhikara.api.get_link_options', { doctype, limit: 1000 })
      .then((rows) => {
        cache[doctype].options = (rows || []).map((r) => {
          const title = r[Object.keys(r).find((k) => k !== 'name')]
          return { label: title || r.name, value: r.name, ...(title && title !== r.name ? { description: r.name } : {}) }
        })
      })
      .catch(() => {
        // no list now (offline, or no access): the picker shows "No results"
      })
      .finally(() => {
        cache[doctype].loading = false
      })
  }
  return cache[doctype]
}
