import { shallowRef } from 'vue'

// The short code that starts this site's city doctype names ("HYD"), set from the branding and read by the text
// helper that hides it. A module of its own with no imports, so those two do not have to import each other.
export const doctypePrefix = shallowRef(null)
