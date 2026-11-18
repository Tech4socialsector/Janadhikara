import { shallowRef } from 'vue'

// The languages this site offers, set from the branding (the city's own list) and read by the language switcher and the
// translation loader. A module of its own with no imports, so those do not have to import the branding.
// Until the branding has loaded - or when a city names none - the original three.
export const DEFAULT_LANGUAGES = ['en', 'as', 'hi']
export const offeredLanguages = shallowRef(DEFAULT_LANGUAGES)

// Every language the app has text for, by its own name (for a visitor who is not signed in yet, with nothing to fetch).
export const LANGUAGE_NAMES = { en: 'English', as: 'অসমীয়া', hi: 'हिन्दी', te: 'తెలుగు' }
