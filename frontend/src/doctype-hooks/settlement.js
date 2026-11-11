import { session } from '@/data/session'

// Settlement: the partner organisation of the signed-in worker is filled in on a new record.

export function onLoad(values, ctx) {
  // Name of the staff: the signed-in user (their name and login id), when empty.
  if (!values.orw_name && session.user) values.orw_name = session.user
  if (values.partner_organization) return
  ctx
    .call('janadhikara.api.get_household_field_defaults')
    .then((res) => {
      const data = res?.message ?? res
      if (data?.partner_organization && !values.partner_organization) values.partner_organization = data.partner_organization
    })
    .catch(() => {})
}

// 1.1 to 1.4: changing a level clears the levels below it, since they are listed only for the level above.
const BELOW = {
  s1_municipal_corporation: ['s1_zone', 's1_circle', 's1_ward'],
  s1_zone: ['s1_circle', 's1_ward'],
  s1_circle: ['s1_ward'],
}

// 2.2: the total population is Male + Female + Others, added up as they are entered.
const POPULATION = ['s2_population_male', 's2_population_female', 's2_population_others']

export function onFieldChange(fieldname, values) {
  if (BELOW[fieldname]) for (const f of BELOW[fieldname]) values[f] = null
  else if (POPULATION.includes(fieldname)) values.s2_total_population = POPULATION.reduce((total, f) => total + (Number(values[f]) || 0), 0)
}
