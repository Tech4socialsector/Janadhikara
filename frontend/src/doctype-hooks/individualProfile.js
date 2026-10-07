// Individual Profile: the age follows the date of birth, and questions 2 to 5 follow the chosen household.
import { call } from 'frappe-ui'
import { INDIVIDUAL_NOTICE, confirmConsent } from '@/utils/dpdpNotice'

// Age (completed years) follows the date of birth, as it does on the server.
function ageFromDob(dob) {
  const born = new Date(dob)
  if (!dob || Number.isNaN(born.getTime())) return null
  const now = new Date()
  let age = now.getFullYear() - born.getFullYear()
  if (now.getMonth() < born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() < born.getDate())) age -= 1
  return Math.max(0, age)
}

export function onLoad(values) {
  if (values.date_of_birth) values.age = ageFromDob(values.date_of_birth)
}

export function onFieldChange(fieldname, values, ctx) {
  if (fieldname === 'date_of_birth') values.age = ageFromDob(values.date_of_birth)
  confirmConsent(fieldname, values, ctx, INDIVIDUAL_NOTICE)
  if (fieldname === 'household' && values.household) {
    call('frappe.client.get_value', {
      doctype: 'Household Profile',
      filters: { name: values.household },
      fieldname: ['hhid', 'partner_organization', 'settlement', 'respondent_name', 'pregnant_woman', 'person_with_disability'],
    })
      .then((res) => {
        const h = res?.message ?? res
        if (!h) return
        values.hhid = h.hhid
        values.implementing_org = h.partner_organization
        values.settlement_intervention_unit = h.settlement
        if (!values.respondent_name) values.respondent_name = h.respondent_name
        values.household_has_pregnant = h.pregnant_woman === 'Yes' ? 1 : 0
        values.household_has_disability = h.person_with_disability === 'Yes' ? 1 : 0
      })
      .catch(() => {})
  }
}
