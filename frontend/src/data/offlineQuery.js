// The part of Frappe's list query the app uses, run over the copy kept on this phone
// (data/offlineStore.js) plus what was saved here and is waiting to upload (data/offlineQueue.js).
// Shared by the offline API (data/offlineApi.js) and the offline dashboard (data/offlineDashboard.js).
import { getDocs } from '@/data/offlineStore'
import { queue } from '@/data/offlineQueue'

export const parsed = (v) => {
  if (typeof v !== 'string') return v
  const s = v.trim()
  if (!s.startsWith('{') && !s.startsWith('[')) return v
  try {
    return JSON.parse(s)
  } catch {
    return v
  }
}

// The documents of a doctype: the downloaded ones, edits waiting to upload shown over them, and
// records made on this phone first. null when the doctype is not on the phone at all.
export async function localDocs(doctype) {
  let docs = await getDocs(doctype)
  const waiting = queue.value.filter((i) => i.doctype === doctype)
  if (!docs && !waiting.length) return null
  docs = docs || []
  const edits = new Map(waiting.filter((i) => i.action === 'update').map((i) => [i.name, i.doc]))
  docs = docs.map((d) => (edits.has(d.name) ? { ...d, ...edits.get(d.name), name: d.name } : d))
  const created = waiting
    .filter((i) => i.action === 'insert')
    .map((i) => ({ ...i.doc, name: i.tempName, modified: new Date(i.createdAt).toISOString().replace('T', ' ').slice(0, 19), __offline: true }))
  return [...created, ...docs]
}

const norm = (v) => (v === undefined || v === null ? '' : v)
function test(actual, op, value) {
  const a = norm(actual)
  switch (String(op).toLowerCase()) {
    case '=': return String(a) === String(norm(value))
    case '!=': return String(a) !== String(norm(value))
    case 'like': {
      const re = new RegExp('^' + String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/%/g, '.*').replace(/_/g, '.') + '$', 'i')
      return re.test(String(a))
    }
    case 'not like': return !test(actual, 'like', value)
    case 'in': return (Array.isArray(value) ? value : String(value).split(',')).map(String).includes(String(a))
    case 'not in': return !test(actual, 'in', value)
    case '>': return a > value
    case '<': return a < value
    case '>=': return a >= value
    case '<=': return a <= value
    case 'between': return Array.isArray(value) && a !== '' && a >= value[0] && a <= value[1]
    case 'is': return String(value).toLowerCase() === 'set' ? a !== '' : a === ''
    default: return true
  }
}

// { field: value } | { field: [op, value] } | [[field, op, value]] | [[doctype, field, op, value]] | "name"
export function matches(doc, filters) {
  const f = parsed(filters)
  if (!f) return true
  if (typeof f === 'string') return doc.name === f
  if (Array.isArray(f)) return f.every((c) => (c.length >= 4 ? test(doc[c[1]], c[2], c[3]) : test(doc[c[0]], c[1], c[2])))
  return Object.entries(f).every(([field, cond]) => (Array.isArray(cond) ? test(doc[field], cond[0], cond[1]) : test(doc[field], '=', cond)))
}

export function sortDocs(docs, orderBy) {
  const [field, dir] = String(orderBy || 'modified desc').trim().split(/\s+/)
  const sign = String(dir).toLowerCase() === 'asc' ? 1 : -1
  return [...docs].sort((a, b) => {
    const x = norm(a[field]), y = norm(b[field])
    return x === y ? 0 : (x > y ? 1 : -1) * sign
  })
}

export function pick(doc, fields) {
  const list = parsed(fields)
  if (!Array.isArray(list) || !list.length || list.includes('*')) return doc
  return Object.fromEntries([['name', doc.name], ...list.map((f) => [f, doc[f]])])
}

export async function query(doctype, params) {
  const docs = await localDocs(doctype)
  if (!docs) return null
  return sortDocs(docs.filter((d) => matches(d, params.filters ?? params.filter)), params.order_by)
}

export const textOf = (v) => (v && typeof v === 'object' ? Object.values(v).map(textOf).join(' ') : String(v ?? ''))

// { answer: how many }, blank answers left out (GROUP BY field)
export function countBy(docs, field) {
  const out = {}
  for (const d of docs) {
    const v = d[field]
    if (v !== undefined && v !== null && v !== '') out[v] = (out[v] || 0) + 1
  }
  return out
}
