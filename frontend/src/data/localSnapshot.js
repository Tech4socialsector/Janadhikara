// A tiny copy of a few small, non-sensitive reads (the module list, branding) so the app can
// still draw its home screen with no connection. vueuse's fetch falls back to `initialData`
// when a request fails, which is exactly what is wanted offline.
const PREFIX = 'janadhikara-snapshot-'

export function readSnapshot(key) {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function saveSnapshot(key, data) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(data))
  } catch {
    // storage full or blocked - the app simply has no offline copy of this read
  }
}

export function clearSnapshots() {
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(PREFIX))
      .forEach((k) => localStorage.removeItem(PREFIX + k.slice(PREFIX.length)))
  } catch {
    // nothing to clear
  }
}

// useCall options with the saved copy wired in: shown if the request fails, refreshed on success.
export function withSnapshot(key, options) {
  const saved = readSnapshot(key)
  const onSuccess = options.onSuccess
  return {
    ...options,
    ...(saved ? { initialData: { data: saved } } : {}),
    onSuccess(data) {
      saveSnapshot(key, data)
      onSuccess?.(data)
    },
  }
}
