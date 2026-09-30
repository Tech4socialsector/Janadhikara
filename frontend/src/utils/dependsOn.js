// Evaluates Frappe's own `depends_on` DocField convention - the same
// mechanism desk itself uses (see apps/frappe/frappe/public/js/frappe/
// utils/utils.js's frappe.utils.eval and frappe/form/layout.js's
// evaluate_depends_on_value): a string prefixed "eval:" is JS, evaluated
// with `doc` (and `parent`, for a child-table row) in scope, e.g.
// "eval:doc.age>14" or "eval:doc.gender=='Other'". Anything else is
// treated the way desk does for a bare fieldname - truthy value (or a
// non-empty array, for a Table/Table MultiSelect) means "show".
//
// This is what makes doctype JSON metadata's own depends_on/
// mandatory_depends_on properties actually take effect in this app's
// generic, metadata-driven form rendering - without this, every
// conditional field/section a doctype declares would just always render,
// regardless of its condition (which is exactly what happened before this
// existed - see Family Member Profile's ~50 conditional questions).
const cache = new Map()

export function evaluateDependsOn(expression, values, parent) {
  if (!expression) return true
  if (typeof expression === 'boolean') return expression

  if (expression.startsWith('eval:')) {
    const code = expression.slice(5)
    let fn = cache.get(code)
    if (!fn) {
      try {
        // eslint-disable-next-line no-new-func
        fn = new Function('doc', 'parent', `let out = ${code}; return out`)
      } catch {
        return true
      }
      cache.set(code, fn)
    }
    try {
      return !!fn(values, parent)
    } catch {
      // A field referenced in the expression not existing yet (e.g. still
      // loading) shouldn't crash the form - default to hidden, same as a
      // thrown expression in desk falling through to a falsy result.
      return false
    }
  }

  // Bare fieldname convention (e.g. "some_checkbox") - truthy value shows
  // the field, same as desk's own fallback branch.
  const value = values?.[expression]
  if (Array.isArray(value)) return value.length > 0
  return !!value
}
