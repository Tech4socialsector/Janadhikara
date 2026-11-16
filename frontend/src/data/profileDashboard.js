// A city's own dashboard, worked out on the phone from the downloaded records, for when there is no connection.
// It reads the same spec as the server (the pack's dashboard spec, see janadhikara.dashboard._profile_dashboard) and
// gives the same figures. Plain functions with no imports, so the rule is one thing to read and to test.

const STATUS_ORDER = ['Partially Completed', 'Completed', 'Revision Needed', 'Validated']

// Python's round() goes to the even neighbour on a tie (12.5 -> 12); Math.round does not. The server decides the figure.
const pyRound = (x) => {
  const floor = Math.floor(x)
  const diff = x - floor
  if (diff < 0.5) return floor
  if (diff > 0.5) return floor + 1
  return floor % 2 === 0 ? floor : floor + 1
}
const byCountThenName = (counts) => (a, b) => counts[b] - counts[a] || (String(a) < String(b) ? -1 : String(a) > String(b) ? 1 : 0)

function dateFilter(filters, field, from, to) {
  if (from && to) filters[field] = ['between', [from, to]]
  else if (from) filters[field] = ['>=', from]
  else if (to) filters[field] = ['<=', to]
}

// A record against the filters used here: a value, or a date range.
function matches(doc, filters) {
  for (const [field, want] of Object.entries(filters)) {
    const have = doc[field]
    if (Array.isArray(want)) {
      const [op, value] = want
      const d = String(have ?? '').slice(0, 10)
      if (op === 'between' && !(d >= value[0] && d <= value[1])) return false
      if (op === '>=' && !(d >= value)) return false
      if (op === '<=' && !(d <= value)) return false
      if (op === '>' && !(Number(have) > value)) return false
    } else if (have !== want) return false
  }
  return true
}

const counted = (docs, field) => {
  const counts = {}
  for (const d of docs) if (d[field] !== null && d[field] !== undefined && d[field] !== '') counts[d[field]] = (counts[d[field]] || 0) + 1
  return counts
}
const total = (docs, field) => docs.reduce((sum, d) => sum + (Math.trunc(Number(d[field])) || 0), 0)

// ctx: { labels: { <doctype>: { name: label } }, asOf }
export function computeProfileDashboard(spec, docs, params, ctx = {}) {
  const dateField = spec.date_field
  const base = {}
  for (const f of spec.filters) if (params[f.key]) base[f.key] = params[f.key]
  dateFilter(base, dateField, params.from_date, params.to_date)
  const mine = docs.filter((d) => matches(d, base))

  const card = (c) => {
    const where = { ...base, ...(c.where || {}) }
    let value
    if (c.op === 'sum') value = c.fields.reduce((sum, f) => sum + total(mine, f), 0)
    else if (c.op === 'percent') value = mine.length ? pyRound((100 * mine.filter((d) => matches(d, where)).length) / mine.length) : 0
    else value = mine.filter((d) => matches(d, where)).length
    return { key: c.key, title: c.title, value, suffix: c.suffix || null, doctype: spec.doctype, filters: where }
  }

  const chart = (c) => {
    const out = { key: c.key, title: c.title, subtitle: c.subtitle || null, kind: c.kind, horizontal: !!c.horizontal, suffix: c.suffix || '', wide: !!c.wide }
    if (c.op === 'monthly') {
      const per = {}
      for (const d of mine) if (d[dateField]) per[String(d[dateField]).slice(0, 7)] = (per[String(d[dateField]).slice(0, 7)] || 0) + 1
      const months = Object.keys(per).sort()
      const monthFilters = (m) => {
        const [y, mo] = m.split('-').map(Number)
        const last = new Date(y, mo, 0).getDate()
        return { ...base, [dateField]: ['between', [`${m}-01`, `${m}-${String(last).padStart(2, '0')}`]] }
      }
      return {
        ...out, months, series: [{ name: c.series, values: months.map((m) => per[m]) }],
        rows: months.map((m) => ({ month: m, filters: monthFilters(m) })),
        table: { headers: ['Month', c.series], rows: months.map((m) => [m, per[m]]) },
      }
    }
    let rows
    let unit = 'Profiles'
    if (c.op === 'counts') {
      const counts = counted(mine, c.field)
      const order = c.order === 'status' ? STATUS_ORDER : c.order
      const keys = order ? order.filter((k) => k in counts) : Object.keys(counts).sort(byCountThenName(counts))
      const shown = (c.labels && ctx.labels?.[c.labels.doctype]) || {}
      rows = keys.map((k) => ({ label: shown[k] || k, count: counts[k], filters: { ...base, [c.field]: k } }))
      if (c.limit) rows = rows.slice(0, c.limit)
    } else if (c.op === 'sums') {
      unit = 'Houses'
      rows = c.items.map(([label, field]) => ({ label, count: total(mine, field), filters: { ...base, [field]: ['>', 0] } }))
    } else {
      rows = c.items.map(([label, field]) => {
        const answers = counted(mine, field)
        const asked = Object.values(answers).reduce((a, b) => a + b, 0)
        const have = answers.Yes || 0
        return { label, have, asked, percent: asked ? pyRound((100 * have) / asked) : 0, count: have, filters: { ...base, [field]: 'Yes' } }
      })
    }
    out.table =
      c.op === 'yes_share'
        ? { headers: ['Service', 'Yes (%)', 'Yes', 'Answered'], rows: rows.map((r) => [r.label, r.percent, r.have, r.asked]) }
        : { headers: ['Category', unit], rows: rows.map((r) => [r.label, r.count]) }
    out.rows = rows
    return out
  }

  return {
    ...(ctx.asOf ? { offline_as_of: ctx.asOf } : {}),
    kind: 'profile', doctype: spec.doctype, default_columns: spec.default_columns,
    cards: spec.cards.map(card), charts: spec.charts.map(chart),
  }
}

// The filters the dashboard offers: ctx.options[doctype] = [{ value, label }] for each master, ctx.statuses = enabled status names.
export function profileFilterOptions(spec, ctx) {
  const statuses = ctx.statuses || []
  const orderedStatuses = [...STATUS_ORDER.filter((n) => statuses.includes(n)), ...statuses.filter((n) => !STATUS_ORDER.includes(n)).sort()]
  return {
    mode: 'profile',
    ...(ctx.asOf ? { offline_as_of: ctx.asOf } : {}),
    filters: spec.filters.map((f) => ({
      key: f.key,
      label: f.label,
      options: f.source === 'status' ? orderedStatuses.map((s) => ({ value: s, label: s })) : ctx.options?.[f.source.doctype] || [],
    })),
    can_export: {},
  }
}
