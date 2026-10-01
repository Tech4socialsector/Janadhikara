// Runs the Field Function Mapping rules configured for a form: when a
// trigger field fires (e.g. a map field's 'geo-changed'), every enabled rule
// for that doctype + field runs its built-in function (see
// utils/fieldFunctions.js) and writes each output into the target field the
// rule maps it to. Nothing is guessed from field names any more - a field
// only gets filled if a rule explicitly maps an output to it.
//
// Used by the main form (DoctypeForm.vue) and by the child-table row editor
// (ChildTable.vue, with its own row as `values`), so rules on a child doctype
// work the same way.
//
// Outputs aimed at Link fields (State, District, ...) are matched to an
// existing master record by name, top-down through the function's
// `hierarchy`; a name with no matching record is left blank and reported,
// never created.
import { ref } from 'vue'
import { call, toast } from 'frappe-ui'
import { FIELD_FUNCTIONS } from '@/utils/fieldFunctions'
import { rulesFor, rulesUsingInput } from '@/data/fieldFunctionRules'
import { session } from '@/data/session'

async function resolveLink(doctype, text, filters) {
  if (!text) return null
  try {
    const res = await call('frappe.desk.search.search_link', {
      doctype,
      txt: text,
      page_length: 10,
      filters: filters ? JSON.stringify(filters) : undefined,
    })
    const rows = Array.isArray(res) ? res : res?.message || res?.results || []
    const needle = String(text).trim().toLowerCase()
    const hay = (r) => `${r.value} ${r.description || ''}`.toLowerCase()
    return (
      rows.find((r) => r.value?.toLowerCase() === needle || (r.description || '').toLowerCase() === needle) ||
      rows.find((r) => hay(r).includes(needle)) ||
      null
    )?.value || null
  } catch {
    return null
  }
}

export function useFieldFunctions({ doctype, fields, values }) {
  const running = ref(false)

  async function applyRule(rule, value, inputValue) {
    const fn = FIELD_FUNCTIONS[rule.function_name]
    if (!fn) return
    const outputs = await fn.run(value, { user: session.user, inputValue })

    const hierarchy = fn.hierarchy || {}
    const resolved = {} // output -> the value actually written (for parents)
    const missing = []

    // Parents before children, so a District is looked up inside the State
    // just written. Outputs with no parent keep their mapped order.
    const depth = (output) => (hierarchy[output] ? 1 + depth(hierarchy[output]) : 0)
    const ordered = [...rule.mappings].sort((a, b) => depth(a.output) - depth(b.output))

    for (const { output, target_field, only_if_empty } of ordered) {
      if (!(output in outputs)) continue
      const field = fields.value.find((f) => f.fieldname === target_field)
      if (!field) continue
      const raw = outputs[output]
      const current = values[target_field]
      if (only_if_empty && current !== undefined && current !== null && current !== '') continue

      if (field.fieldtype === 'Link' && field.options && output !== 'captured_by') {
        if (!raw) continue
        const parent = hierarchy[output]
        const filters = parent && resolved[parent] ? { [parent]: resolved[parent] } : undefined
        const match = await resolveLink(field.options, raw, filters)
        if (match) {
          values[target_field] = match
          resolved[output] = match
        } else {
          missing.push(`${field.label || target_field}: ${raw}`)
        }
      } else {
        // Skip empty address parts rather than wiping what's already there.
        if ((raw === '' || raw === undefined) && output !== 'boundary') continue
        values[target_field] = raw
        resolved[output] = raw
      }
    }

    const message = fn.summary?.(outputs)
    if (message) toast.success(message)
    if (missing.length) toast.info(`Not in master data, left blank - ${missing.join('; ')}`)
  }

  // `payload` is { fieldname, value } - the field that just changed and its
  // new value. Runs every rule triggered by that field, plus every rule that
  // merely reads it as its "Also Uses Field" (e.g. Distance Between Points
  // re-runs when either of its two map fields changes).
  async function runTrigger({ fieldname, value }) {
    const dt = doctype.value ?? doctype
    const direct = rulesFor(dt, fieldname)
    const indirect = rulesUsingInput(dt, fieldname).filter((r) => !direct.includes(r))
    if (!direct.length && !indirect.length) return
    running.value = true
    try {
      for (const rule of direct) {
        await applyRule(rule, value, values[rule.mappings.find((m) => m.input_field)?.input_field])
      }
      for (const rule of indirect) {
        // The changed field is the rule's extra input, not its trigger.
        await applyRule(rule, values[rule.trigger_field], value)
      }
    } finally {
      running.value = false
    }
  }

  return { runTrigger, running }
}
