// The Dashboard's numbers worked out on the phone from the downloaded records, for when there is no
// connection. It mirrors janadhikara.dashboard (get_dashboard / get_filter_options): the same cards,
// charts and filters, over the same records the person may see - as of the last download.
import { getDocs, getTable, storeInfo } from '@/data/offlineStore'
import { localDocs, matches, countBy } from '@/data/offlineQuery'

const HOUSEHOLD = 'Household Profile'
const INDIVIDUAL = 'Individual Profile'
const STATUS_ORDER = ['Partially Completed', 'Completed', 'Revision Needed', 'Validated']
const AGE_GROUPS = [['0-5', 0, 5], ['6-14', 6, 14], ['15-17', 15, 17], ['18-35', 18, 35], ['36-59', 36, 59], ['60+', 60, 200]]
const DOCUMENTS = [
  ['doc_aadhaar', 'Aadhaar'], ['doc_ration_card', 'Ration card'], ['doc_voter_id', 'Voter ID'], ['doc_bank_account', 'Bank account'],
  ['doc_pan', 'PAN'], ['doc_birth_certificate', 'Birth certificate'], ['doc_eshram', 'E-Shram'], ['doc_income_certificate', 'Income certificate'],
]

const asOf = () => storeInfo.value?.generated || null

// A record is counted on its Date; where the form has none, on when it was created.
const dateField = (docs) => (docs.some((d) => 'record_date' in d) ? 'record_date' : 'creation')

function dateFilter(filters, field, from, to) {
  if (from && to) filters[field] = ['between', [from, to]]
  else if (from) filters[field] = ['>=', from]
  else if (to) filters[field] = ['<=', to]
}
const ofMonth = (docs, field, filters) => {
  const per = {}
  for (const d of docs.filter((x) => matches(x, filters))) {
    const v = d[field]
    if (v) per[String(v).slice(0, 7)] = (per[String(v).slice(0, 7)] || 0) + 1
  }
  return per
}
const monthFilters = (field, filters, month) => {
  const [y, m] = month.split('-').map(Number)
  const last = new Date(y, m, 0).getDate()
  return { ...filters, [field]: ['between', [`${month}-01`, `${month}-${String(last).padStart(2, '0')}`]] }
}
const series = (counts, order, filters, fieldname) => {
  // biggest first; equal counts in alphabetical order (the order the server's GROUP BY gives them)
  const keys = order || Object.keys(counts).sort().sort((a, b) => counts[b] - counts[a])
  return keys
    .filter((k) => counts[k] || order)
    .map((k) => ({ label: k, count: counts[k] || 0, ...(fieldname ? { filters: { ...filters, [fieldname]: k } } : {}) }))
}

export async function offlineDashboard(p) {
  const households = (await localDocs(HOUSEHOLD)) || []
  const individuals = (await localDocs(INDIVIDUAL)) || []
  const hhDate = dateField(households)
  const indDate = dateField(individuals)

  const hh = {}
  const ind = {}
  if (p.settlement) { hh.settlement = p.settlement; ind.settlement_intervention_unit = p.settlement }
  if (p.partner_organization) { hh.partner_organization = p.partner_organization; ind.implementing_org = p.partner_organization }
  dateFilter(hh, hhDate, p.from_date, p.to_date)
  dateFilter(ind, indDate, p.from_date, p.to_date)
  if (p.gender) ind.gender = p.gender
  if (p.validation_status) ind.validation_status = p.validation_status
  if (p.household_status) hh.household_status = p.household_status
  for (const [label, low, high] of AGE_GROUPS) if (label === p.age_group) ind.age = ['between', [low, high]]

  const H = households.filter((d) => matches(d, hh))
  const I = individuals.filter((d) => matches(d, ind))
  const members = H.reduce((sum, d) => sum + (Number(d.member_count) || 0), 0)
  const status = countBy(I, 'validation_status')
  const validated = status.Validated || 0
  const completed = (status.Completed || 0) + validated

  const ages = {}
  for (const [age, count] of Object.entries(countBy(I, 'age'))) {
    for (const [label, low, high] of AGE_GROUPS) if (low <= Number(age) && Number(age) <= high) ages[label] = (ages[label] || 0) + count
  }
  const outOfSchoolFilters = { ...ind, out_of_school_status: ['is', 'set'] }
  const outOfSchool = I.filter((d) => matches(d, { out_of_school_status: ['is', 'set'] })).length

  const documents = DOCUMENTS.map(([fieldname, label]) => {
    const answers = countBy(I, fieldname)
    const asked = Object.values(answers).reduce((a, b) => a + b, 0)
    const have = answers.Yes || 0
    return { label, have, asked, percent: asked ? Math.round((100 * have) / asked) : 0, filters: { ...ind, [fieldname]: 'Yes' } }
  })

  const hhPer = ofMonth(households, hhDate, hh)
  const indPer = ofMonth(individuals, indDate, ind)
  const months = [...new Set([...Object.keys(hhPer), ...Object.keys(indPer)])].sort()
  const card = (key, title, value, doctype, filters, suffix = null) => ({ key, title, value, suffix, doctype, filters })
  const pct = (n) => (I.length ? Math.round((100 * n) / I.length) : 0)

  return {
    offline_as_of: asOf(),
    cards: [
      card('households', 'Households', H.length, HOUSEHOLD, hh),
      card('members', 'Members (as told by households)', members, HOUSEHOLD, hh),
      card('individuals', 'Individual profiles', I.length, INDIVIDUAL, ind),
      card('completed', 'Profiles completed', pct(completed), INDIVIDUAL, { ...ind, validation_status: ['in', ['Completed', 'Validated']] }, '%'),
      card('validated', 'Profiles validated', pct(validated), INDIVIDUAL, { ...ind, validation_status: 'Validated' }, '%'),
      card('out_of_school', 'Children out of school', outOfSchool, INDIVIDUAL, outOfSchoolFilters),
      card('disability', 'Persons with disability', countBy(I, 'disability_in_family').Yes || 0, INDIVIDUAL, { ...ind, disability_in_family: 'Yes' }),
      card('women_not_working', 'Women not in full-time work', countBy(I, 'women_full_time_work').No || 0, INDIVIDUAL, { ...ind, women_full_time_work: 'No' }),
    ],
    household_status: series(countBy(H, 'household_status'), null, hh, 'household_status'),
    household_documentation: series(countBy(H, 'validation_status'), STATUS_ORDER, hh, 'validation_status'),
    gender: series(countBy(I, 'gender'), null, ind, 'gender'),
    age_groups: AGE_GROUPS.map(([label, low, high]) => ({ label, count: ages[label] || 0, filters: { ...ind, age: ['between', [low, high]] } })),
    education: series(countBy(I, 'highest_education'), null, ind, 'highest_education'),
    documentation: series(status, STATUS_ORDER, ind, 'validation_status'),
    documents,
    occupation: series(countBy(I, 'occupation_1'), null, ind, 'occupation_1').slice(0, 10),
    monthly: months.map((m) => ({
      month: m, Households: hhPer[m] || 0, Individuals: indPer[m] || 0,
      household_filters: monthFilters(hhDate, hh, m), individual_filters: monthFilters(indDate, ind, m),
    })),
  }
}

// The options a Select field offers, from its form layout (kept by the offline engine).
async function selectOptions(doctype, fieldname, fallbackDocs) {
  try {
    const res = await fetch(`/api/v2/doctype/${encodeURIComponent(doctype)}/meta?`)
    const meta = (await res.json())?.data
    const options = meta?.fields?.find((f) => f.fieldname === fieldname)?.options
    if (options) return options.split('\n').filter(Boolean)
  } catch {
    // fall through to what the records hold
  }
  return Object.keys(countBy(fallbackDocs || [], fieldname))
}

export async function offlineFilterOptions() {
  const settlements = (await getDocs('Settlement')) || []
  const partners = (await getDocs('Partner Details')) || []
  const statuses = ((await getTable('Validation Status'))?.docs || []).filter((d) => d.enabled === 1 || d.enabled === true).map((d) => d.name)
  const households = (await localDocs(HOUSEHOLD)) || []
  return {
    offline_as_of: asOf(),
    settlements: settlements.map((s) => ({ value: s.name, label: s.settlement_name || s.name })).sort((a, b) => a.label.localeCompare(b.label)),
    partners: partners.map((p) => ({ value: p.name, label: p.organization_name || p.name })),
    genders: ['Female', 'Male', 'Other'],
    age_groups: AGE_GROUPS.map((g) => g[0]),
    household_statuses: await selectOptions(HOUSEHOLD, 'household_status', households),
    validation_statuses: [...STATUS_ORDER.filter((n) => statuses.includes(n)), ...statuses.filter((n) => !STATUS_ORDER.includes(n)).sort()],
    can_export: {},
  }
}
