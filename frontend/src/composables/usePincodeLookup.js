// Resolves a 6-digit Indian Pincode to its State/District via Nominatim
// (OpenStreetMap's free, keyless geocoder - already used for reverse-
// geocoding a map pin in GeoLocationField.vue, so this reuses the same
// already-reachable service rather than a second one). Kept as one shared
// composable rather than copy-pasted per doctype, since Pincode-driven
// State/District fill applies the same way anywhere a doctype has all
// three fields (currently Household profile, but generic by fieldname
// convention so it costs nothing to apply elsewhere later).
//
// State/District are plain Data fields backed by IndiaGeoField.vue's own
// dropdown (see useIndiaGeoData) rather than a Frappe Link/master
// doctype, so unlike an earlier version of this file there's nothing to
// find-or-create here - Nominatim's answer is stored as-is, and the
// field's own "change it here if it's wrong" description covers the case
// where its wording doesn't exactly match the dropdown's own list.
import { ref } from 'vue'

export function usePincodeLookup() {
  const looking = ref(false)
  const lookupError = ref('')

  async function lookupPincode(pincode) {
    lookupError.value = ''
    if (!/^\d{6}$/.test(pincode || '')) return null

    looking.value = true
    try {
      // accept-language=en - see GeoLocationField.vue's resolveAddress for
      // why (Nominatim otherwise answers in the location's own local
      // language, which would give State/District values in a different
      // script than the dropdown they're meant to match).
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?postalcode=${pincode}&country=India&format=jsonv2&addressdetails=1&accept-language=en`,
        { headers: { Accept: 'application/json' } },
      )
      if (!res.ok) {
        lookupError.value = 'Could not look up this pincode.'
        return null
      }
      const results = await res.json()
      const address = results?.[0]?.address
      if (!address) {
        lookupError.value = 'No matching location found for this pincode.'
        return null
      }
      const state = address.state || ''
      // Nominatim's address breakdown doesn't have a single fixed key for
      // "district" across every country/region - state_district is the
      // usual one for India, county is the fallback some areas return
      // instead.
      const district = address.state_district || address.county || ''
      return { state, district }
    } catch {
      lookupError.value = 'Could not look up this pincode.'
      return null
    } finally {
      looking.value = false
    }
  }

  return { looking, lookupError, lookupPincode }
}
