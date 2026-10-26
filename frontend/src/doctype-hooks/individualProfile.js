// Individual Profile: the age follows the date of birth, and questions 2 to 4 follow the chosen household.
import { call } from 'frappe-ui'
import { session } from '@/data/session'
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

// Q18 offers the occupations that fit the person's gender (as the Settlement Profile lists them separately for
// men and women). "Others" stays available for anything not listed; Other / no gender yet sees the full list.
const NOT_FOR_WOMEN = [
  'Taxi Driver', 'Bus Driver', 'Bus Conductor', 'Bus Ticket Collector', 'Truck Driver', 'Auto Driver',
  'Rickshaw Puller', 'E-Rickshaw', 'Porter', 'Barber', 'Cobbler', 'Slaughterhouse Worker', 'Manual Scavenger',
]
const NOT_FOR_MEN = ['Household Responsibility/family care work', 'House Help-Domestic work/Cook', 'Beautician Services']
function occupationsFor(values, ctx) {
  const hidden = values.gender === 'Female' ? NOT_FOR_WOMEN : values.gender === 'Male' ? NOT_FOR_MEN : []
  ctx?.setFieldOptions?.('occupation_1', hidden.length ? (o) => !hidden.includes(o) : null)
}

export function onLoad(values, ctx) {
  // Name of the ORW: the signed-in user (their name and login id), when empty.
  if (!values.orw_name && session.user) values.orw_name = session.user
  // The signed-in worker's organisation, until a household is chosen (the household's own organisation then takes over).
  if (!values.implementing_org && ctx?.call) {
    ctx
      .call('janadhikara.api.get_household_field_defaults')
      .then((res) => {
        const data = res?.message ?? res
        if (data?.partner_organization && !values.implementing_org) values.implementing_org = data.partner_organization
      })
      .catch(() => {})
  }
  if (values.date_of_birth) values.age = ageFromDob(values.date_of_birth)
  occupationsFor(values, ctx)
}

export function onFieldChange(fieldname, values, ctx) {
  if (fieldname === 'date_of_birth') values.age = ageFromDob(values.date_of_birth)
  if (fieldname === 'gender') occupationsFor(values, ctx)
  confirmConsent(fieldname, values, ctx, INDIVIDUAL_NOTICE)
  if (fieldname === 'household' && values.household) {
    call('frappe.client.get_value', {
      doctype: 'Household Profile',
      filters: { name: values.household },
      fieldname: ['hhid', 'partner_organization', 'settlement', 'pregnant_woman', 'person_with_disability'],
    })
      .then((res) => {
        const h = res?.message ?? res
        if (!h) return
        values.hhid = h.hhid
        values.implementing_org = h.partner_organization
        values.settlement_intervention_unit = h.settlement
        values.household_has_pregnant = h.pregnant_woman === 'Yes' ? 1 : 0
        values.household_has_disability = h.person_with_disability === 'Yes' ? 1 : 0
      })
      .catch(() => {})
  }
}
