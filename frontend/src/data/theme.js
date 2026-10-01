import { ref, watchEffect } from 'vue'

const STORAGE_KEY = 'janadhikara-theme'

export const currentTheme = ref(localStorage.getItem(STORAGE_KEY) || 'light')

let firstRun = true

watchEffect(() => {
  const isDark = currentTheme.value === 'dark'
  const root = document.documentElement

  // Switching theme must repaint everything in the same frame. frappe-ui's
  // Sidebar (and its items/header) animate `transition-all` for 150-300ms, so
  // on a switch the page content flipped instantly while the sidebar was
  // still fading - visibly out of step. A short-lived class turns every
  // transition off for the duration of the change (see index.css), then
  // normal hover/collapse animations come straight back. Skipped on the very
  // first run, which just applies the saved theme before anything is shown.
  if (!firstRun) root.classList.add('theme-switching')

  // Two dark-mode conventions need satisfying at once: our own `dark:`
  // Tailwind utility classes key off the `.dark` class (tailwind.config.js
  // darkMode: 'class'), while frappe-ui's own components (Sidebar, Button,
  // Dropdown, ...) key off `[data-theme="dark"]` (its own preset's
  // darkMode). Without both, frappe-ui's built-ins silently never re-theme.
  root.classList.toggle('dark', isDark)
  root.setAttribute('data-theme', isDark ? 'dark' : 'light')
  localStorage.setItem(STORAGE_KEY, currentTheme.value)

  // The installed app's status bar / title bar takes this colour, so it should
  // match the header in whichever theme is showing.
  const themeColor = document.querySelector('meta[name="theme-color"]')
  if (themeColor) themeColor.setAttribute('content', isDark ? '#171717' : '#ffffff')

  if (!firstRun) {
    // Force the new styles to be computed while transitions are still off,
    // then release the lock after the frame has painted.
    void getComputedStyle(root).color
    requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('theme-switching')))
  }
  firstRun = false
})

export function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
}
