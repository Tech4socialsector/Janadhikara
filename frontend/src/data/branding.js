import { computed, watchEffect } from 'vue'
import { useCall } from 'frappe-ui'
import { withSnapshot } from '@/data/localSnapshot'
import { currentTheme } from '@/data/theme'
import defaultLogo from '@/assets/default-logo.png'
import { online } from '@/data/connection'
import { appIconDataUrl } from '@/data/offlinePack'

// The app's configurable name/logo, from App Setting (allow_guest=True
// so the Login page can also show it before authentication).
export const brandingResource = useCall(
  withSnapshot('app-branding', {
    url: '/api/v2/method/janadhikara.api.get_app_branding',
    method: 'GET',
    cacheKey: 'janadhikara-app-branding',
  }),
)

// Single source of truth for "which logo to render right now" - every
// header/login-page consumer wants the same light/dark pick, and
// get_app_branding already falls app_logo_dark back to app_logo server-side,
// so this only needs to choose between the two, not reimplement that
// fallback too.
// Janadhikara's own icon, used whenever no logo has been uploaded (and a
// partner without a logo of its own falls back to App Setting's, then to this).
export const DEFAULT_LOGO = defaultLogo

export const appLogo = computed(
  () =>
    (!online.value && appIconDataUrl.value) ||
    (currentTheme.value === 'dark'
      ? brandingResource.data?.app_logo_dark || brandingResource.data?.app_logo
      : brandingResource.data?.app_logo) || DEFAULT_LOGO,
)

// App Setting's Accent Color (a hex string, e.g. "#111827") drives the
// app's primary buttons, active nav state, filter badges, and the AI
// assistant's own message bubble/avatar - every spot that used to
// hardcode gray-900 as "this is the brand color", not the many other
// gray-900/gray-100 pairs elsewhere that are just body text or a dark-mode
// surface fill and were deliberately left alone (see the CSS below for
// exactly which classes this actually touches).
//
// Falls back to the same near-black default the DocField itself declares
// (see app_setting.json's accent_color field) so the app still looks
// exactly as it did before this setting existed when App Setting hasn't
// been saved yet (brandingResource.data is null before its first fetch
// resolves) or the field is left blank.
const DEFAULT_ACCENT = '#111827'
export const accentColor = computed(() => brandingResource.data?.accent_color || DEFAULT_ACCENT)

// A CSS custom property, not a Tailwind class swap - frappe-ui's own
// Button variant="solid" and this app's hand-rolled accent spots (see
// index.css) both read var(--app-accent)/var(--app-accent-hover) so one
// value picked in App Setting re-colors every one of them at once, without
// a full Tailwind rebuild per color (impossible at runtime anyway - the
// color is admin-configurable data, not known at build time).
//
// Hover/active shades are computed from the same base color (not a
// second/third color field) - darkened for light backgrounds, lightened
// for dark ones - matching how the gray-900/gray-800/gray-700 hover
// progression this replaced already worked, just generalized to any hex
// input rather than hardcoded gray steps.
function shade(hex, percent) {
  const clean = hex.replace('#', '')
  const num = parseInt(clean.length === 3 ? clean.replace(/(.)/g, '$1$1') : clean, 16)
  const r = Math.max(0, Math.min(255, ((num >> 16) & 0xff) + percent))
  const g = Math.max(0, Math.min(255, ((num >> 8) & 0xff) + percent))
  const b = Math.max(0, Math.min(255, (num & 0xff) + percent))
  return `rgb(${r}, ${g}, ${b})`
}

watchEffect(() => {
  const color = accentColor.value
  const root = document.documentElement.style
  root.setProperty('--app-accent', color)
  // Darker on hover in light mode (mirrors gray-900 -> gray-800 -> gray-700),
  // lighter on hover in dark mode (mirrors gray-100 -> gray-200 -> gray-300) -
  // same direction reversal the old hardcoded pairs already had between
  // their light/dark variants.
  const isDark = currentTheme.value === 'dark'
  root.setProperty('--app-accent-hover', shade(color, isDark ? 24 : -24))
  root.setProperty('--app-accent-active', shade(color, isDark ? 44 : -44))
})
