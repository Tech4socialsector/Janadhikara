import { useCall } from 'frappe-ui'

// Enabled Field Function Mapping rules - which built-in function runs when a
// field on a doctype changes, and which output goes into which field.
// Configured in Settings > Field Function Mapping.
//
// Shape (janadhikara.api.get_field_function_rules):
// [{ target_doctype, trigger_field, function_name,
//    mappings: [{ output, target_field, input_field, only_if_empty }] }]
export const fieldFunctionRulesResource = useCall({
  url: '/api/v2/method/janadhikara.api.get_field_function_rules',
  method: 'GET',
  cacheKey: 'janadhikara-field-function-rules',
})

export function rulesFor(doctype, triggerField) {
  return (fieldFunctionRulesResource.data || []).filter(
    (r) => r.target_doctype === doctype && r.trigger_field === triggerField,
  )
}

// Rules that don't fire on `field` itself but read it as a mapping's
// "Also Uses Field".
export function rulesUsingInput(doctype, field) {
  return (fieldFunctionRulesResource.data || []).filter(
    (r) =>
      r.target_doctype === doctype &&
      r.trigger_field !== field &&
      r.mappings.some((m) => m.input_field === field),
  )
}
