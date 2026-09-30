import { ref } from 'vue'

// Free, keyless, static JSON dataset of every Indian state/UT and its
// districts (35 states, no API key or backend master doctype involved) -
// served off jsdelivr's GitHub CDN, which mirrors the repo's raw files
// with caching and no rate limit at this app's scale. Fetched once and
// shared across every State/District field on the page, rather than
// re-fetched per field instance.
const GEO_DATA_URL =
  'https://cdn.jsdelivr.net/gh/sab99r/Indian-States-And-Districts@master/states-and-districts.json'

const states = ref([])
const districtsByState = ref({})
const loading = ref(false)
const error = ref('')
let fetchPromise = null

function normalize(data) {
  const stateNames = []
  const byState = {}
  for (const entry of data?.states || []) {
    stateNames.push(entry.state)
    byState[entry.state] = entry.districts || []
  }
  stateNames.sort((a, b) => a.localeCompare(b))
  return { stateNames, byState }
}

async function fetchGeoData() {
  if (fetchPromise) return fetchPromise
  fetchPromise = (async () => {
    loading.value = true
    error.value = ''
    try {
      const res = await fetch(GEO_DATA_URL)
      if (!res.ok) throw new Error('bad response')
      const data = await res.json()
      const { stateNames, byState } = normalize(data)
      states.value = stateNames
      districtsByState.value = byState
    } catch {
      error.value = 'Could not load the list of states/districts.'
    } finally {
      loading.value = false
    }
  })()
  return fetchPromise
}

export function useIndiaGeoData() {
  if (!fetchPromise) fetchGeoData()
  return { states, districtsByState, loading, error }
}
