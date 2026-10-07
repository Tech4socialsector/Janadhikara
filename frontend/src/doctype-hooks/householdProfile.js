import { HOUSEHOLD_NOTICE, todayString } from '@/utils/dpdpNotice'

// Household Profile: capture what the logged-in worker already implies.
//
// On a new household, the server (janadhikara.api.get_household_field_defaults)
// matches the logged-in user to their partner-worker record and lists every
// place they're tagged to work - a settlement, or one of its intervention
// units, via the Settlement's Workers table. This fills the partner and
// worker, and, when there is exactly one place, the settlement and its
// intervention unit too (with several, the worker picks).
// Anyone who isn't a partner worker (an admin, say) gets nothing filled.
// Only empty fields are filled on load, so nothing the user typed is lost.

let places = []

function fillIfEmpty(values, fieldname, value) {
  if (value && !values[fieldname]) values[fieldname] = value
}

function applyPlace(values, place, { overwrite = false } = {}) {
  const set = overwrite ? (f, v) => v && (values[f] = v) : (f, v) => fillIfEmpty(values, f, v)
  set('settlement', place.settlement)
}

export function onLoad(values, ctx) {
  places = []
  ctx
    .call('janadhikara.api.get_household_field_defaults')
    .then((res) => {
      const data = res?.message ?? res
      if (!data?.assigned_worker) return
      places = data.assignments || []
      fillIfEmpty(values, 'partner_organization', data.partner_organization)
      fillIfEmpty(values, 'assigned_worker', data.assigned_worker)
      if (places.length === 1) applyPlace(values, places[0])
    })
    .catch(() => {
      // best-effort convenience - the form still works fully by hand
    })
}


// The respondent is the head of the family unless a head is named: the head's name follows the respondent
// while it is empty or still the respondent's previous name.
let lastRespondent = ''
export function onFieldChange(fieldname, values, ctx) {
  // Choosing "Going Ahead" first shows the DPDP notice. Consent is recorded when it is confirmed; if it is
  // closed without confirming, the choice is undone and the personal questions stay hidden.
  if (fieldname === 'availability_for_survey' && values.availability_for_survey === 'Going Ahead' && !Number(values.consent_given) && ctx?.confirmNotice) {
    setTimeout(() => {
      ctx.confirmNotice({
        ...HOUSEHOLD_NOTICE,
        onConfirm: () => {
          values.consent_given = 1
          values.consent_mode = values.consent_mode || 'Verbal (recorded)'
          values.consent_date = todayString()
        },
        onCancel: () => {
          values.availability_for_survey = null
        },
      })
    }, 0)
  }
  // The partner follows the chosen settlement.
  if (fieldname === 'settlement' && values.settlement) {
    ctx.call('frappe.client.get_value', { doctype: 'Settlement', filters: { name: values.settlement }, fieldname: 'partner_organization' })
      .then((res) => {
        const partner = (res?.message ?? res)?.partner_organization
        if (partner) values.partner_organization = partner
      })
      .catch(() => {})
  }
  if (fieldname !== 'respondent_name') return
  if (!values.household_head_name || values.household_head_name === lastRespondent) {
    values.household_head_name = values.respondent_name
  }
  lastRespondent = values.respondent_name || ''
}
