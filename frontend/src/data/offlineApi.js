// With no connection the app keeps working: lists, records, counts, searches, link titles and the
// dashboard are answered from the one copy this phone holds (data/offlineStore.js) plus records saved
// here and waiting to upload (data/offlineQueue.js). Nothing new is stored for this: it only reads those.
//
// It sits in front of window.fetch, so every screen gets it without knowing: online, requests go
// to the server untouched; with no network (or when a request fails to reach the server) the same
// request is answered locally. Only reads are answered; a write is never faked.
import { getTable } from '@/data/offlineStore'
import { localDocs, query, pick, parsed, textOf } from '@/data/offlineQuery'
import { offlineDashboard, offlineFilterOptions } from '@/data/offlineDashboard'

let realFetch = null

function describe(input, init = {}) {
  if (typeof input !== 'string' && !(input instanceof URL)) return null
  const url = new URL(String(input), window.location.origin)
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return null
  const params = {}
  url.searchParams.forEach((v, k) => (params[k] = v))
  if (typeof init.body === 'string') {
    try {
      Object.assign(params, JSON.parse(init.body))
    } catch {
      new URLSearchParams(init.body).forEach((v, k) => (params[k] = v))
    }
  } else if (init.body) {
    return null // an upload or other form body: never answered locally
  }
  const path = url.pathname
  let m
  if ((m = path.match(/^\/api\/(?:v2\/)?method\/(.+)$/))) return { v2: path.startsWith('/api/v2/'), kind: 'method', method: decodeURIComponent(m[1]), params }
  if ((m = path.match(/^\/api\/v2\/document\/([^/]+)\/([^/]+)$/)) && String(init.method || 'GET').toUpperCase() === 'GET')
    return { v2: true, kind: 'doc', doctype: decodeURIComponent(m[1]), name: decodeURIComponent(m[2]), params }
  if ((m = path.match(/^\/api\/v2\/document\/([^/]+)$/)) && String(init.method || 'GET').toUpperCase() === 'GET')
    return { v2: true, kind: 'list', doctype: decodeURIComponent(m[1]), params }
  return null
}

const respond = (req, value) =>
  new Response(JSON.stringify(req.v2 ? { data: value } : { message: value }), {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'X-Offline': '1' },
  })

// ---- What is answered ---------------------------------------------------------------------------
async function answer(req) {
  const p = req.params
  if (req.kind === 'list') {
    const rows = await query(req.doctype, p)
    if (!rows) return null
    const start = Number(p.start || 0)
    const limit = Number(p.limit || p.limit_page_length || 20)
    return respond(req, rows.slice(start, start + limit).map((d) => pick(d, p.fields)))
  }
  if (req.kind === 'doc') {
    const doc = (await localDocs(req.doctype))?.find((d) => d.name === req.name)
    return doc ? respond(req, doc) : null
  }
  switch (req.method) {
    case 'frappe.client.get_count': {
      const rows = await query(p.doctype, p)
      return rows ? respond(req, rows.length) : null
    }
    case 'frappe.client.get_list': {
      const rows = p.doctype === 'ToDo' ? [] : await query(p.doctype, p) // tasks are never kept on the phone
      if (!rows) return null
      const start = Number(p.limit_start || p.start || 0)
      const limit = Number(p.limit_page_length || p.limit || 20)
      return respond(req, rows.slice(start, start + limit).map((d) => pick(d, p.fields)))
    }
    case 'frappe.client.get': {
      const doc = (await localDocs(p.doctype))?.find((d) => d.name === p.name)
      return doc ? respond(req, doc) : null
    }
    case 'frappe.client.get_value': {
      const rows = await query(p.doctype, { filters: parsed(p.filters) })
      if (!rows?.length) return null
      const fields = parsed(p.fieldname)
      const doc = rows[0]
      return respond(req, Array.isArray(fields) ? Object.fromEntries(fields.map((f) => [f, doc[f]])) : { [fields]: doc[fields] })
    }
    case 'janadhikara.api.get_link_titles': {
      const names = parsed(p.names) || []
      const docs = await localDocs(p.doctype)
      const titleField = (await getTable(p.doctype))?.title_field
      if (!docs || !titleField) return null
      const byName = new Map(docs.map((d) => [d.name, d[titleField]]))
      return respond(req, Object.fromEntries(names.filter((n) => byName.get(n)).map((n) => [n, byName.get(n)])))
    }
    case 'janadhikara.api.search_record_names': {
      const docs = await localDocs(p.doctype)
      if (!docs) return null
      const q = String(p.txt || '').toLowerCase()
      return respond(req, docs.filter((d) => textOf(d).toLowerCase().includes(q)).map((d) => d.name).slice(0, 2000))
    }
    case 'frappe.desk.search.search_link': {
      const docs = await localDocs(p.doctype)
      if (!docs) return null
      const q = String(p.txt || '').toLowerCase()
      const titleField = (await getTable(p.doctype))?.title_field
      const rows = docs.filter((d) => matches(d, parsed(p.filters)) && (!q || textOf(d).toLowerCase().includes(q))).slice(0, Number(p.page_length || 20))
      return respond(req, rows.map((d) => ({ value: d.name, description: titleField && d[titleField] ? d[titleField] : '' })))
    }
    case 'frappe.client.has_permission':
      // the server still checks every change when it is uploaded
      return respond(req, { has_permission: p.perm_type !== 'delete' })
    case 'janadhikara.dashboard.get_dashboard':
      return respond(req, await offlineDashboard(p))
    case 'janadhikara.dashboard.get_filter_options':
      return respond(req, await offlineFilterOptions())
    case 'janadhikara.dashboard.can_export':
      return respond(req, false)
    case 'frappe.desk.form.activity.get_activity_timeline':
      return respond(req, { creation: [], communications: [], comments: [], versions: [] })
  }
  return null
}

const offlineNow = () => typeof navigator !== 'undefined' && navigator.onLine === false

async function proxied(input, init = {}) {
  const req = describe(input, init)
  if (!req) return realFetch(input, init)
  if (offlineNow()) return (await answer(req).catch((e) => (console.warn('offline answer failed', req.kind, req.doctype || req.method, e), null))) || realFetch(input, init)
  try {
    return await realFetch(input, init)
  } catch (e) {
    if (init.signal?.aborted) throw e
    const local = await answer(req).catch((e) => (console.warn('offline answer failed', req.kind, req.doctype || req.method, e), null))
    if (local) return local
    throw e
  }
}

export function installOfflineApi() {
  if (realFetch || typeof window === 'undefined') return
  realFetch = window.fetch.bind(window)
  window.fetch = proxied
}
