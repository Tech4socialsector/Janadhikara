// Settlement: the partner organisation of the signed-in worker is filled in on a new record.

export function onLoad(values, ctx) {
  if (values.partner_organization) return
  ctx
    .call('janadhikara.api.get_household_field_defaults')
    .then((res) => {
      const data = res?.message ?? res
      if (data?.partner_organization && !values.partner_organization) values.partner_organization = data.partner_organization
    })
    .catch(() => {})
}
