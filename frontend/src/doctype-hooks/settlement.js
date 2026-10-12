import { session } from '@/data/session'

// Settlement: the partner organisation of the signed-in worker is filled in on a new record.

export function onLoad(values, ctx) {
  // Name of the ORW: the signed-in user (their name and login id), when empty.
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

// 7.1 and 7.2 follow the housing counts above: the houses (6.x.1) and the families (6.x.2) of every housing
// type are added up as they are entered. The totals stay editable - a worker can overwrite them, and they are
// worked out again the next time one of the counts changes.
const HOUSE_COUNTS = [
  'q6_1_1_no_temporary_shacks',
  'q6_2_1_no_tin_roof_houses_with',
  'q6_3_1_no_tin_roof_houses_with',
  'q6_4_1_no_houses_with_stilt_dwellings',
  'q6_5_1_no_houses_with_stilt_dwellings',
  'q6_6_1_no_hill_slope_terraced_structures',
  'q6_7_1_no_concrete_houses',
  'q6_8_1_no_houses_as_tenement_constructed',
  'q6_9_1_no_tenements_residing_tin_roof',
]
const FAMILY_COUNTS = [
  'q6_1_2_no_families_living_these_type',
  'q6_2_2_no_families_living_these_type',
  'q6_3_2_no_families_living_these_type',
  'q6_4_2_no_families_living_these_type',
  'q6_5_2_no_families_living_these_type',
  'q6_6_2_no_families_living_these_type',
  'q6_7_2_no_families_living_these_type',
  'q6_8_2_no_families_living_these_type',
  'q6_9_2_no_families_living_these_type',
]
const sum = (values, fields) => fields.reduce((total, f) => total + (Number(values[f]) || 0), 0)

export function onFieldChange(fieldname, values) {
  if (HOUSE_COUNTS.includes(fieldname)) values.q7_1_indicate_total_number_houses_physical = sum(values, HOUSE_COUNTS)
  else if (FAMILY_COUNTS.includes(fieldname)) values.q7_2_specify_total_number_families_currently = sum(values, FAMILY_COUNTS)
}
