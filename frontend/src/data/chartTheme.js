import { computed } from 'vue'
import { currentTheme } from '@/data/theme'

// Chart look for the dashboard: one validated palette (the data-viz reference palette - every adjacent
// pair clears the colour-blind and normal-vision separation checks in both modes), text always in ink
// tokens (never in a series colour), hairline recessive grid, and a surface-coloured gap between
// touching marks.

const CATEGORICAL = {
  light: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'],
  dark: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'],
}
const TOKENS = {
  // surface = the chart card's own background, so gaps and rings blend into it
  light: { surface: '#ffffff', primary: '#111827', secondary: '#4b5563', muted: '#6b7280', grid: '#eceae6', axis: '#d6d3cd', hover: '#256abf', tooltip: '#ffffff', tooltipBorder: '#e5e7eb' },
  dark: { surface: '#111827', primary: '#f9fafb', secondary: '#d1d5db', muted: '#9ca3af', grid: '#232b38', axis: '#374151', hover: '#86b6ef', tooltip: '#1f2937', tooltipBorder: '#374151' },
}

export const chartTheme = computed(() => {
  const mode = currentTheme.value === 'dark' ? 'dark' : 'light'
  return { mode, colors: CATEGORICAL[mode], ...TOKENS[mode] }
})

// Colour follows the thing, never its rank: a label keeps the slot it first got, so filtering the
// dashboard (fewer categories) never repaints the ones that remain.
const slots = new Map()
export function slotFor(label) {
  if (!slots.has(label)) slots.set(label, slots.size % 8)
  return slots.get(label)
}

export const FONT = 'Inter, ui-sans-serif, system-ui, sans-serif'

// Tooltip rows are built from escaped text - labels come from user-entered answers.
export const esc = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])

export function tooltipBox(t, title, rows) {
  const body = rows
    .map(
      (r) =>
        `<div style="display:flex;align-items:center;gap:8px;margin-top:4px">` +
        `<span style="width:10px;height:3px;border-radius:2px;background:${r.color}"></span>` +
        `<span style="color:${t.primary};font-weight:600;font-variant-numeric:tabular-nums">${esc(r.value)}</span>` +
        `<span style="color:${t.secondary}">${esc(r.name)}</span></div>`,
    )
    .join('')
  return `<div style="font-family:${FONT};font-size:12px"><div style="color:${t.muted}">${esc(title)}</div>${body}</div>`
}
