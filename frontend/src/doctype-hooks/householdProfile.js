// Household Profile: capture what the logged-in worker already implies.
//
// On a new household, the server (janadhikara.api.get_household_field_defaults)
// matches the logged-in user to their partner-worker record and lists every
// place they're tagged to work - a settlement, or one of its intervention
// units, via the Settlement's Workers table - with the Survey Field Unit
// covering it. This fills the partner and worker, and:
//   - exactly one place  -> the settlement, intervention unit, survey field
//     unit and survey are filled straight away
//   - several places     -> the field unit follows as soon as the worker
//     picks the settlement (and unit), from the same list
// Anyone who isn't a partner worker (an admin, say) gets nothing filled.
// Only empty fields are filled on load, so nothing the user typed is lost.

let places = []

function fillIfEmpty(values, fieldname, value) {
  if (value && !values[fieldname]) values[fieldname] = value
}

function applyPlace(values, place, { overwrite = false } = {}) {
  const set = overwrite ? (f, v) => v && (values[f] = v) : (f, v) => fillIfEmpty(values, f, v)
  set('settlement', place.settlement)
  set('settlement_intervention_unit', place.settlement_intervention_unit)
  set('survey_field_unit', place.survey_field_unit)
  set('survey', place.survey)
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

export function onFieldChange(fieldname, values) {
  if (fieldname !== 'settlement' && fieldname !== 'settlement_intervention_unit') return
  if (!places.length || !values.settlement) return

  const unit = values.settlement_intervention_unit
  const matches = places.filter(
    (p) =>
      p.settlement === values.settlement &&
      p.survey_field_unit &&
      (!unit || !p.settlement_intervention_unit || p.settlement_intervention_unit === unit),
  )
  // Only when it's unambiguous - otherwise the worker picks the field unit.
  if (matches.length === 1) {
    values.survey_field_unit = matches[0].survey_field_unit
    fillIfEmpty(values, 'survey', matches[0].survey)
    fillIfEmpty(values, 'settlement_intervention_unit', matches[0].settlement_intervention_unit)
  }
}
