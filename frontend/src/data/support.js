// The help desk's server calls (janadhikara.helpdesk). Each returns the method's own answer.
import { call } from 'frappe-ui'
import { ref } from 'vue'

const run = async (method, args) => {
  const res = await call(`janadhikara.helpdesk.${method}`, args || {})
  return res?.message ?? res
}

export const supportOptions = ref(null)
export async function loadSupportOptions() {
  supportOptions.value = await run('get_options')
  return supportOptions.value
}
export const listTickets = (args) => run('list_tickets', args)
export const getTicket = (name) => run('get_ticket', { name })
export const createTicket = (args) => run('create_ticket', args)
export const addReply = (ticket, message, is_internal = 0, to = null, cc = null) => run('add_reply', { ticket, message, is_internal, to, cc })
export const updateTicket = (args) => run('update_ticket', args)
export const getOverview = () => run('get_overview')
export const deleteTickets = (names) => run('delete_tickets', { names })

// Upload one file as a private attachment and return its URL (for the ticket's Attachment field).
export async function uploadAttachment(file) {
  const body = new FormData()
  body.append('file', file, file.name)
  body.append('is_private', '1')
  const res = await fetch('/api/method/upload_file', { method: 'POST', body, headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' } })
  const json = await res.json()
  if (!res.ok || !json.message?.file_url) throw new Error(json.exception || 'The file could not be uploaded.')
  return json.message.file_url
}

export const STATUS_STYLE = {
  Open: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300',
  'In Progress': 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  'Waiting on Requester': 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300',
  Resolved: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300',
  Closed: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}
export const PRIORITY_STYLE = {
  Low: 'text-gray-500',
  Medium: 'text-blue-600 dark:text-blue-400',
  High: 'text-orange-600 dark:text-orange-400',
  Urgent: 'font-semibold text-red-600 dark:text-red-400',
}
export const timeAgo = (value) => {
  const d = new Date(String(value).replace(' ', 'T'))
  const mins = Math.round((Date.now() - d.getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`
  if (mins < 43200) return `${Math.round(mins / 1440)} d ago`
  return d.toLocaleDateString([], { dateStyle: 'medium' })
}

export const STATUS_DOT = {
  Open: 'bg-blue-500',
  'In Progress': 'bg-amber-500',
  'Waiting on Requester': 'bg-purple-500',
  Resolved: 'bg-green-500',
  Closed: 'bg-gray-400',
}
export const PRIORITY_DOT = { Low: 'bg-gray-300', Medium: 'bg-blue-400', High: 'bg-orange-500', Urgent: 'bg-red-600' }
export const initials = (n) => String(n || '?').split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('')
const AVATARS = [
  'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
  'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
  'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
  'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
  'bg-pink-100 text-pink-700 dark:bg-pink-500/20 dark:text-pink-300',
]
export const avatarClass = (user) => AVATARS[[...String(user || '')].reduce((h, c) => h + c.charCodeAt(0), 0) % AVATARS.length]
