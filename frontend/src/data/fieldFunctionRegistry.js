import { useCall } from 'frappe-ui'

// The built-in field functions and what each accepts/produces
// (janadhikara.api.get_field_function_registry) - lets the field pickers on
// Field Function Mapping offer only field types a function can use.
// `immediate: false`: only the pickers need it, so it's fetched on demand
// rather than on every form load.
//
// Shape: { "<Function>": { description, trigger_fieldtypes,
//                          input_fieldtypes?, outputs: { key: { label, fieldtypes } } } }
export const fieldFunctionRegistryResource = useCall({
  url: '/api/v2/method/janadhikara.api.get_field_function_registry',
  method: 'GET',
  immediate: false,
  cacheKey: 'janadhikara-field-function-registry',
})
