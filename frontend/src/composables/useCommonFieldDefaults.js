import { watch } from 'vue'
import { session } from '@/data/session'

// Cross-doctype default-value rules that apply purely from a field being
// present - kept out of DoctypeForm.vue so that file stays about
// rendering/saving a form, not about what these specific business
// defaults are. Each rule only ever fills an empty field, so it never
// overwrites a value a doctype-specific hook (see doctype-hooks/) or the
// user has already set.
//
// `doctype: null` means "every doctype with this fieldname"; a specific
// `doctype` scopes the rule to just that one doctype, for a fieldname that
// means something different on that particular doctype than the generic
// rule assumes.
//
// Each rule's value comes from `resource`: something duck-typing a
// useCall's { data } shape, read reactively - needs a watch to catch it
// resolving after the field itself becomes visible. (Plain synchronous
// defaults like "today's date" don't need a rule at all - see
// resolveFrappeDefault and its use in applyDefaults below, which reads
// them straight off the field's own metadata instead.) Empty for now -
// add an entry here when a doctype needs a cross-doctype business default
// beyond what its own field.default already covers.
const RULES = []

// Frappe's own field-level `default` property (set in the DocType editor,
// same as Household profile's survay_date, Mental Health's
// date_of_registration, and Family members' own date field all already
// declare: `"default": "Today"`) - resolved the same handful of special
// keywords Frappe desk's own frappe.model.get_default_value() does
// (see apps/frappe/frappe/public/js/frappe/model/create_new.js), rather
// than a fixed list of fieldnames this file would need updating every
// time a doctype adds a new auto-captured date/user field. Any other
// literal default (a Select's first option value, a fixed Data string,
// etc.) is returned as-is, same as Frappe desk does.
function resolveFrappeDefault(rawDefault) {
  const value = String(rawDefault)
  if (value === '__user' || value.toLowerCase() === 'user') return session.user
  if (value === 'Today') {
    const d = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  }
  return rawDefault
}

// `fields`/`values` are the same refs/reactive objects DoctypeForm.vue
// already builds - passed in rather than re-derived so this stays a plain
// function of the form's own state instead of a second source of truth.
// `onApplied` (optional) fires every time applyDefaults() actually runs -
// not just the one call DoctypeForm.vue makes itself from its doc-load
// watcher, but also the two internal watchers below, which can re-run
// this later and asynchronously (a resource resolving after mount). A
// caller tracking "unsaved changes" needs to know about all of those, not
// just the first: a default filled in programmatically is not a user
// edit and shouldn't flip that indicator on by itself.
export function useCommonFieldDefaults({ doctype, fields, values, isNew, onApplied }) {
  // A doctype-specific rule for a fieldname takes over from the generic
  // (doctype: null) rule for that same fieldname entirely, rather than
  // both applying and racing to fill the field first - for a fieldname
  // that means something different on one particular doctype than the
  // generic rule assumes.
  const doctypeSpecificFieldnames = new Set(
    RULES.filter((r) => r.doctype === doctype).map((r) => r.fieldname),
  )
  const applicableRules = RULES.filter(
    (rule) =>
      rule.doctype === doctype ||
      (rule.doctype === null && !doctypeSpecificFieldnames.has(rule.fieldname)),
  )

  function applyDefaults() {
    if (!isNew) return
    // Every field's own declared `default` (Frappe's native, doctype-level
    // mechanism - see resolveFrappeDefault above) applies first and
    // generically, before the business-specific RULES below: whichever
    // doctype adds a field with e.g. "default": "Today" just works,
    // without this file needing a new fieldname-keyed rule added for it.
    for (const field of fields.value) {
      if (!field.default) continue
      if (values[field.fieldname]) continue
      const defaultValue = resolveFrappeDefault(field.default)
      if (defaultValue) values[field.fieldname] = defaultValue
    }
    for (const rule of applicableRules) {
      if (!fields.value.some((f) => f.fieldname === rule.fieldname)) continue
      if (values[rule.fieldname]) continue
      const defaultValue = rule.resource.data
      if (defaultValue) values[rule.fieldname] = defaultValue
    }
    onApplied?.()
  }

  // Re-run whenever a rule's resource resolves AND whenever `fields` itself
  // changes - `fields` is a computed() over the doctype's meta fetch, which
  // is still empty on first render and only becomes populated once that
  // fetch resolves (see useFormFields). For a rule whose resource is
  // already set well before the form even mounts, the resource's own
  // watch never fires again - without also watching `fields`,
  // applyDefaults()'s one call from the doc-load watcher below would run
  // while fields.value is still [], find no matching field, and never get
  // a second chance. This is also the only re-trigger the generic
  // field.default pass above ever needs - it has no resource of its own
  // to watch, just field metadata that's already covered here.
  watch(fields, applyDefaults)
  for (const rule of applicableRules) {
    watch(() => rule.resource.data, applyDefaults)
  }

  return { applyCommonFieldDefaults: applyDefaults }
}
