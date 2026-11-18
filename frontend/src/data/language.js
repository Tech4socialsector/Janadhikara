import { computed, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { session } from '@/data/session'
import { online } from '@/data/connection'
import { offeredLanguages, LANGUAGE_NAMES } from '@/data/cityLanguages'

// The app's language: chosen from the switcher in the top bar, remembered on
// this device (so it works offline) and saved on the user's profile when online.
const LIST_KEY = 'janadhikara-languages'
const CHOICE_KEY = 'janadhikara-language'

const read = (key) => {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
const write = (key, value) => {
  try {
    localStorage.setItem(key, value)
  } catch {
    // not remembered
  }
}

function cachedLanguages() {
  try {
    return JSON.parse(read(LIST_KEY) || 'null') || undefined
  } catch {
    return undefined
  }
}

export const languagesResource = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Language',
    filters: { enabled: 1 },
    fields: ['name', 'language_name'],
    order_by: 'language_name asc',
    limit_page_length: 0,
  },
  // only once signed in: Frappe refuses this list to a signed-out visitor (a 403 in the server log on the login page)
  auto: false,
  cache: 'janadhikara-languages-resource',
  transform: (data) => data.map((l) => ({ label: l.language_name, value: l.name })),
  onSuccess: (data) => write(LIST_KEY, JSON.stringify(data)),
})

// Languages to offer, falling back to the last list seen when offline. Which ones is the city's choice (Guwahati:
// English, Assamese and Hindi; Hyderabad: English and Telugu - see city_packs/), whatever other languages the site has
// enabled. The list comes with the branding (data/cityLanguages.js).
const ownNames = () => offeredLanguages.value.map((value) => ({ label: LANGUAGE_NAMES[value] || value, value }))
export const languages = computed(() => {
  const list = (languagesResource.data || cachedLanguages() || []).filter((l) => offeredLanguages.value.includes(l.value))
  // the list kept on this device may be of another city's languages: then the offered ones by their own names
  return list.length === offeredLanguages.value.length ? list : ownNames()
})
// Started once every module has loaded (`session` is part of a circular import, see settingsEntries.js).
queueMicrotask(() =>
  watch(
    () => session.user,
    (user) => user && !languagesResource.data && languagesResource.fetch(),
    { immediate: true },
  ),
)

const chosen = ref(read(CHOICE_KEY))
let unsynced = false

export const appLanguage = computed(() => {
  const language = chosen.value || session.user_language || 'en'
  return offeredLanguages.value.includes(language) ? language : 'en'
})

const setLanguageResource = createResource({
  url: 'frappe.client.set_value',
  makeParams: (language) => ({ doctype: 'User', name: session.user, fieldname: 'language', value: language }),
  onSuccess() {
    unsynced = false
    session.user_language = chosen.value
  },
  onError() {
    unsynced = true
  },
})

export function setUserLanguage(language) {
  chosen.value = language
  write(CHOICE_KEY, language)
  document.documentElement.lang = language
  if (online.value && session.user) setLanguageResource.submit(language)
  else unsynced = true
}

// Back online after choosing offline: save the choice on the profile.
watch(online, (isOnline) => {
  if (isOnline && unsynced && chosen.value && session.user) setLanguageResource.submit(chosen.value)
})

document.documentElement.lang = appLanguage.value
