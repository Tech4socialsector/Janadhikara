// The Dashboard's numbers worked out on the phone from the downloaded records, for when there is no
// connection. It mirrors janadhikara.dashboard (get_dashboard / get_filter_options): the same cards,
// charts and filters, over the same Settlement records the person may see - as of the last download.
import { getDocs, getTable, storeInfo } from '@/data/offlineStore'
import { localDocs, matches, countBy } from '@/data/offlineQuery'

const SETTLEMENT = 'Settlement'
const STATUS_ORDER = ['Partially Completed', 'Completed', 'Revision Needed', 'Validated']
const TOTALS = [
  ['households', 'Households', ['s2_total_households']],
  ['population', 'Population', ['s2_total_population']],
  ['migrant_households', 'Migrant households', ['s2_migrant_household_count']],
  ['children_0_6', 'Children aged 0-6', ['s2_children_0_3', 's2_children_3_6']],
  ['disability', 'Persons with disabilities', ['s2_persons_with_disabilities']],
]
const ANSWER_CARDS = [
  ['eviction_risk', 'Settlements at risk of eviction', 's3_eviction_risk', 'Yes'],
  ['recommended', 'Recommended for the program', 's10_recommended', 'Yes'],
]
const CHARTS = [
  ['validation_status', 'Profile status', 'validation_status', 'donut', true],
  ['notified', 'Notified status', 's1_notified', 'donut', true],
  ['category', 'Category of settlement', 's1_category', 'hbar', true],
  ['land_type', 'Government or private land', 's1_land_type', 'donut', true],
  ['zone', 'Settlements by zone', 's1_zone', 'hbar', false],
  ['located_close_to', 'Located close to', 's1_located_close_to', 'hbar', true],
  ['migrant_type', 'Type of migrants', 's2_migrant_type', 'donut', true],
  ['recommended', 'Recommended for the program', 's10_recommended', 'donut', true],
]

const asOf = () => storeInfo.value?.generated || null

// The options a Select field offers, from the form layout (kept by the offline engine).
let metaFields = null
async function selectOptions(fieldname) {
  try {
    if (!metaFields) {
      const res = await fetch(`/api/v2/doctype/${encodeURIComponent(SETTLEMENT)}/meta?`)
      metaFields = (await res.json())?.data?.fields || []
    }
    const options = metaFields.find((f) => f.fieldname === fieldname)?.options
    return options ? options.split('\n').filter(Boolean) : []
  } catch {
    return []
  }
}

const rows = (counts, filters, fieldname, order) => {
  // in the field's own order, or biggest first (equal counts alphabetically, as the server's GROUP BY gives them)
  const keys = order
    ? [...order.filter((k) => counts[k]), ...Object.keys(counts).filter((k) => !order.includes(k)).sort()]
    : Object.keys(counts).sort().sort((a, b) => counts[b] - counts[a])
  return keys.map((k) => ({ label: k, count: counts[k], filters: { ...filters, [fieldname]: k } }))
}

export async function offlineDashboard(p) {
  const all = (await localDocs(SETTLEMENT)) || []
  const filters = {}
  for (const [field, value] of [
    ['partner_organization', p.partner_organization], ['s1_zone', p.zone], ['s1_ward', p.ward],
    ['s1_category', p.category], ['validation_status', p.validation_status],
  ]) if (value) filters[field] = value
  if (p.from_date && p.to_date) filters.record_date = ['between', [p.from_date, p.to_date]]
  else if (p.from_date) filters.record_date = ['>=', p.from_date]
  else if (p.to_date) filters.record_date = ['<=', p.to_date]

  const S = all.filter((d) => matches(d, filters))
  const card = (key, title, value, cardFilters, suffix = null) => ({ key, title, value, suffix, doctype: SETTLEMENT, filters: cardFilters })
  const cards = [card('settlements', 'Settlements profiled', S.length, filters)]
  for (const [key, title, fields] of TOTALS) {
    cards.push(card(key, title, S.reduce((sum, d) => sum + fields.reduce((n, f) => n + (Number(d[f]) || 0), 0), 0), filters))
  }
  for (const [key, title, field, answer] of ANSWER_CARDS) cards.push(card(key, title, countBy(S, field)[answer] || 0, { ...filters, [field]: answer }))

  const charts = []
  for (const [key, title, field, kind, ordered] of CHARTS) {
    const order = ordered ? (field === 'validation_status' ? STATUS_ORDER : await selectOptions(field)) : null
    charts.push({ key, title, kind, rows: rows(countBy(S, field), filters, field, order) })
  }

  const perMonth = {}
  for (const d of S) if (d.record_date) perMonth[String(d.record_date).slice(0, 7)] = (perMonth[String(d.record_date).slice(0, 7)] || 0) + 1
  const monthly = Object.keys(perMonth).sort().map((month) => {
    const [y, m] = month.split('-').map(Number)
    const last = new Date(y, m, 0).getDate()
    return { month, count: perMonth[month], filters: { ...filters, record_date: ['between', [`${month}-01`, `${month}-${String(last).padStart(2, '0')}`]] } }
  })
  return { offline_as_of: asOf(), cards, charts, monthly }
}

export async function offlineFilterOptions() {
  const partners = (await getDocs('Partner Details')) || []
  const zones = (await getDocs('Municipal Zone')) || []
  const wards = (await getDocs('Municipal Ward')) || []
  const enabled = (d) => d.enabled === 1 || d.enabled === true
  const statuses = ((await getTable('Validation Status'))?.docs || []).filter(enabled).map((d) => d.name)
  return {
    offline_as_of: asOf(),
    partners: partners.map((p) => ({ value: p.name, label: p.organization_name || p.name })),
    zones: zones.filter(enabled).map((d) => d.name).sort(),
    wards: wards.filter(enabled).map((d) => d.name).sort(),
    categories: await selectOptions('s1_category'),
    validation_statuses: [...STATUS_ORDER.filter((n) => statuses.includes(n)), ...statuses.filter((n) => !STATUS_ORDER.includes(n)).sort()],
    can_export: {},
  }
}
