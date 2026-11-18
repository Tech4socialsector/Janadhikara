// HYD Household Profile: on a new household the signed-in worker and their partner organisation are filled in, and
// when the worker is tagged to exactly one settlement, that settlement too (with several, the worker picks).
// Only empty fields are filled, so nothing the worker typed is lost.
import { session } from '@/data/session'

const fillIfEmpty = (values, fieldname, value) => {
  if (value && !values[fieldname]) values[fieldname] = value
}

export function onLoad(values, ctx) {
  if (session.user) fillIfEmpty(values, 'assigned_worker', session.user)
  ctx
    .call('janadhikara.api.get_household_field_defaults')
    .then((res) => {
      const data = res?.message ?? res
      if (!data?.partner_organization) return
      fillIfEmpty(values, 'partner_organization', data.partner_organization)
      if (data.assignments?.length === 1) fillIfEmpty(values, 'settlement', data.assignments[0].settlement)
    })
    .catch(() => {
      // best-effort convenience - the form still works fully by hand
    })
}
