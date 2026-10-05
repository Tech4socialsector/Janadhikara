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
  set('settlement_intervention_unit', place.settlement_intervention_unit)
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

