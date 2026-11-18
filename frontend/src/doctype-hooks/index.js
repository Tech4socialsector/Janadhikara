// Registry mapping doctype name -> hook module. Each module can export
// onLoad(values, ctx), onFieldChange(fieldname, values, ctx), and
// onChildFieldChange(tableField, fieldname, row, values) - these reimplement
// the doctype's frappe.ui.form.on(...) desk client script, since that API
// doesn't exist for documents edited through this Vue app.
import * as householdProfile from './householdProfile'
import * as individualProfile from './individualProfile'
import * as settlement from './settlement'
import * as settlementProfile from './settlementProfile'
import * as hydHouseholdProfile from './hydHouseholdProfile'
import * as hydIndividualProfile from './hydIndividualProfile'

const HOOKS = {
  'Household Profile': householdProfile,
  'Individual Profile': individualProfile,
  Settlement: settlement,
  'HYD Settlement Profile': settlementProfile,
  'HYD Household Profile': hydHouseholdProfile,
  'HYD Individual Profile': hydIndividualProfile,
}

export function getDoctypeHooks(doctype) {
  return HOOKS[doctype] || null
}
