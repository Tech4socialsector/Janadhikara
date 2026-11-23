import { useDoc } from 'frappe-ui'

// frappe-ui's useDoc has a bug with a record opened a second time more than five minutes after the first: its cache
// entry is stale, so it deletes the entry and then reads it back (undefined.value), which throws while the page is being
// set up and blanks the screen ("This page didn't load properly"). The failed call has already removed the stale entry,
// so asking again starts a fresh load, as for a record opened for the first time.
export function safeUseDoc(options) {
  try {
    return useDoc(options)
  } catch {
    return useDoc(options)
  }
}
