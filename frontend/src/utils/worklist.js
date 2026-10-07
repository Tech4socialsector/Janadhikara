// Small helpers shared by the Worklist page, its calendar and the task hover card.
import { session } from '@/data/session'

// "YYYY-MM-DD" in the user's own timezone (toISOString would shift the day for
// anyone east or west of UTC).
export function ymd(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function plain(html) {
  if (!html) return ''
  // DOMParser builds an inert document: nothing in the markup runs or loads
  const text = new DOMParser().parseFromString(String(html), 'text/html').body.textContent || ''
  return text.replace(/\s+/g, ' ').trim()
}

// A task's short title and its details. Tasks made before titles existed (or by
// other tools) have no title, so the description stands in as the title.
export const taskTitle = (t) => t.task_title || plain(t.description) || '(untitled task)'
export function taskDetails(t) {
  const details = plain(t.description)
  return t.task_title && details && details !== t.task_title ? details : ''
}

export const isOpen = (t) => t.status === 'Open'

// "Jane Doe" from jane.doe@org.org (the ToDo list API carries no full name for the assignee).
export function userLabel(user) {
  if (user === session.user) return 'Me'
  return String(user || '')
    .split('@')[0]
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// "15:30:00" -> "3:30 PM"
export function formatTime(time) {
  if (!time) return ''
  const [h, m] = String(time).split(':').map(Number)
  if (Number.isNaN(h)) return ''
  const d = new Date(2000, 0, 1, h, m || 0)
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

// "Mon, 5 Oct" for a due date.
export function formatDate(date) {
  if (!date) return ''
  return new Date(`${date}T00:00:00`).toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' })
}

// "Overdue · 3d", "Today", "Tomorrow", otherwise the date - with a colour class.
// `text` is the day part, `time` the time of day (when set), `full` both.
export function dueInfo(t, todayKey = ymd(new Date())) {
  if (!t.date) return null
  const time = formatTime(t.task_time)
  const withTime = (text) => ({ text, time, full: time ? `${text} · ${time}` : text })
  if (!isOpen(t)) return { ...withTime(formatDate(t.date)), cls: 'text-ink-gray-5' }
  const days = Math.round((new Date(`${t.date}T00:00:00`) - new Date(`${todayKey}T00:00:00`)) / 86400000)
  if (days < 0) return { ...withTime(`Overdue · ${-days}d`), full: `Overdue · ${-days}d${time ? ` (${formatDate(t.date)}, ${time})` : ` (${formatDate(t.date)})`}`, cls: 'text-ink-red-4' }
  if (days === 0) return { ...withTime('Today'), cls: 'text-ink-amber-3' }
  if (days === 1) return { ...withTime('Tomorrow'), cls: 'text-ink-gray-7' }
  return { ...withTime(formatDate(t.date)), cls: 'text-ink-gray-6' }
}

export const priorityClass = (p) =>
  p === 'High' ? 'bg-surface-red-2 text-ink-red-4' : p === 'Low' ? 'bg-surface-blue-2 text-ink-blue-3' : 'bg-surface-gray-2 text-ink-gray-6'

// Dot / bar colour for a task in the calendar.
export function taskColor(t, todayKey = ymd(new Date())) {
  if (!isOpen(t)) return 'bg-ink-gray-4'
  if (t.date && t.date < todayKey) return 'bg-red-500'
  if (t.priority === 'High') return 'bg-amber-500'
  return 'bg-blue-500'
}
