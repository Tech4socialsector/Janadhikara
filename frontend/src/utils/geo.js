// Shared geo helpers - pure JS, no Vue, reusable from any component or
// composable. Everything works on GeoJSON (what Frappe's Geolocation field
// and the drawn shapes in GeoLocationField.vue are stored as), where circles
// and circle markers are Points carrying `properties.point_type` and
// `properties.radius` (metres), the same way Frappe desk stores them.
//
// Units: area in square metres, lengths/perimeters in metres.

const EARTH_RADIUS_M = 6378137
const toRad = (deg) => (deg * Math.PI) / 180
const round = (n, places = 2) => Math.round(n * 10 ** places) / 10 ** places

export function parseGeoJSON(value) {
  if (!value) return null
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value
    if (parsed?.type === 'FeatureCollection') return parsed
    if (parsed?.type === 'Feature') return { type: 'FeatureCollection', features: [parsed] }
    if (parsed?.type) {
      return { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: parsed }] }
    }
  } catch {
    // not valid GeoJSON
  }
  return null
}

// Great-circle distance between two [lng, lat] points.
function haversine([lng1, lat1], [lng2, lat2]) {
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a))
}

// Straight-line (great-circle) distance in metres between two { lat, lng }
// points, or null if either is missing.
export function distanceBetweenM(a, b) {
  if (!a || !b) return null
  return haversine([a.lng, a.lat], [b.lng, b.lat])
}

// Length of a line / ring, following its points in order.
export function pathLengthM(coords) {
  let total = 0
  for (let i = 1; i < coords.length; i++) total += haversine(coords[i - 1], coords[i])
  return total
}

// Geodesic area of one ring (Chamberlain & Duquette's spherical excess
// approximation - accurate to well under 1% for anything settlement-sized).
export function ringAreaSqM(ring) {
  if (!ring || ring.length < 4) return 0
  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    const [lng1, lat1] = ring[i]
    const [lng2, lat2] = ring[i + 1]
    sum += toRad(lng2 - lng1) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)))
  }
  return Math.abs((sum * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2)
}

function polygonMetrics(rings) {
  const [outer, ...holes] = rings
  const area = ringAreaSqM(outer) - holes.reduce((acc, h) => acc + ringAreaSqM(h), 0)
  const perimeter = rings.reduce((acc, r) => acc + pathLengthM(r), 0)
  return { area: Math.max(area, 0), perimeter }
}

function isCircle(feature) {
  return feature.geometry?.type === 'Point' && feature.properties?.point_type === 'circle'
}

// Area/perimeter of one feature. Markers have neither; a line has a length
// but no area; a circle uses its radius.
export function featureMetrics(feature) {
  const { type, coordinates } = feature.geometry || {}
  if (isCircle(feature)) {
    const r = Number(feature.properties.radius) || 0
    return { area: Math.PI * r * r, perimeter: 2 * Math.PI * r }
  }
  if (type === 'Polygon') return polygonMetrics(coordinates)
  if (type === 'MultiPolygon') {
    return coordinates.map(polygonMetrics).reduce(
      (acc, m) => ({ area: acc.area + m.area, perimeter: acc.perimeter + m.perimeter }),
      { area: 0, perimeter: 0 },
    )
  }
  if (type === 'LineString') return { area: 0, perimeter: pathLengthM(coordinates) }
  return { area: 0, perimeter: 0 }
}

// Total area and perimeter across everything drawn.
export function collectionMetrics(value) {
  const fc = parseGeoJSON(value)
  const features = fc?.features || []
  const totals = features.reduce(
    (acc, f) => {
      const m = featureMetrics(f)
      return { area: acc.area + m.area, perimeter: acc.perimeter + m.perimeter }
    },
    { area: 0, perimeter: 0 },
  )
  return { area: round(totals.area), perimeter: round(totals.perimeter), shapeCount: features.length }
}

function vertices(feature) {
  const { type, coordinates } = feature.geometry || {}
  if (type === 'Point') return [coordinates]
  if (type === 'LineString') return coordinates
  if (type === 'Polygon') return coordinates[0].slice(0, -1)
  if (type === 'MultiPolygon') return coordinates.flatMap((p) => p[0].slice(0, -1))
  return []
}

// A representative [lng, lat] for one feature: polygon centroid (planar
// formula - fine at settlement scale), else the mean of its vertices.
export function featureCentroid(feature) {
  const { type, coordinates } = feature.geometry || {}
  if (type === 'Polygon') {
    const ring = coordinates[0]
    let a = 0
    let cx = 0
    let cy = 0
    for (let i = 0; i < ring.length - 1; i++) {
      const [x1, y1] = ring[i]
      const [x2, y2] = ring[i + 1]
      const cross = x1 * y2 - x2 * y1
      a += cross
      cx += (x1 + x2) * cross
      cy += (y1 + y2) * cross
    }
    if (a !== 0) return [cx / (3 * a), cy / (3 * a)]
  }
  const pts = vertices(feature)
  if (!pts.length) return null
  return [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length]
}

// The point the drawing is "about": the first area shape if there is one
// (a boundary), otherwise the first feature.
export function collectionCentroid(value) {
  const features = parseGeoJSON(value)?.features || []
  const areaShape = features.find((f) => ['Polygon', 'MultiPolygon'].includes(f.geometry?.type) || isCircle(f))
  const pick = areaShape || features[0]
  const c = pick ? featureCentroid(pick) : null
  return c ? { lng: c[0], lat: c[1] } : null
}

// A circle has no polygon form in GeoJSON - approximate it with a 64-gon so
// it can be stored as a boundary like any other area.
function circleToPolygon(feature, steps = 64) {
  const [lng, lat] = feature.geometry.coordinates
  const r = Number(feature.properties.radius) || 0
  const ring = []
  for (let i = 0; i <= steps; i++) {
    const bearing = (2 * Math.PI * i) / steps
    const dLat = (r / EARTH_RADIUS_M) * Math.cos(bearing)
    const dLng = (r / (EARTH_RADIUS_M * Math.cos(toRad(lat)))) * Math.sin(bearing)
    ring.push([lng + (dLng * 180) / Math.PI, lat + (dLat * 180) / Math.PI])
  }
  return { type: 'Polygon', coordinates: [ring] }
}

// The first area shape as a plain GeoJSON Polygon geometry (what a
// "Boundary" JSON field stores), or null when only markers/lines exist.
export function boundaryGeometry(value) {
  const features = parseGeoJSON(value)?.features || []
  for (const f of features) {
    if (f.geometry?.type === 'Polygon') return f.geometry
    if (isCircle(f)) return circleToPolygon(f)
  }
  return null
}

// Turns Nominatim's address breakdown into the fields this app cares about.
// Nominatim has no single fixed key per level across regions, so each level
// lists its usual keys in priority order.
export function normalizeAddress(result) {
  const a = result?.address || {}
  return {
    address: result?.display_name || '',
    pincode: a.postcode || '',
    state: a.state || '',
    district: a.state_district || a.county || '',
    city: a.city || a.town || a.village || a.municipality || '',
    ward: a.suburb || a.city_district || a.neighbourhood || a.quarter || '',
  }
}

// Reverse-geocodes a point via OpenStreetMap's Nominatim (free, keyless -
// the same service the map field already uses). accept-language=en keeps
// names in English, matching this app's English-only master data.
//
// Answers are cached briefly per ~1 m cell: the map field's own pin handler
// and a Field Function Mapping rule can both ask about the same point in the
// same instant, and Nominatim asks for at most one request per second.
const geocodeCache = new Map()
export function reverseGeocode(lat, lng) {
  const key = `${Number(lat).toFixed(5)},${Number(lng).toFixed(5)}`
  if (geocodeCache.has(key)) return geocodeCache.get(key)
  const pending = (async () => {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&addressdetails=1&accept-language=en`,
        { headers: { Accept: 'application/json' } },
      )
      if (!res.ok) return null
      return normalizeAddress(await res.json())
    } catch {
      return null
    }
  })()
  geocodeCache.set(key, pending)
  // Don't keep failures (or stale answers) around.
  pending.then((r) => {
    if (!r) geocodeCache.delete(key)
  })
  setTimeout(() => geocodeCache.delete(key), 60000)
  return pending
}

// Everything derivable from a drawn value in one call: where it is, how big
// it is, its boundary polygon, and the address breakdown for its centre.
//   { latitude, longitude, area, perimeter, boundary, address, pincode,
//     state, district, city, ward }
export async function describeGeoValue(value) {
  const centre = collectionCentroid(value)
  if (!centre) return null
  const { area, perimeter } = collectionMetrics(value)
  const geometry = boundaryGeometry(value)
  const place = (await reverseGeocode(centre.lat, centre.lng)) || {}
  return {
    latitude: round(centre.lat, 9),
    longitude: round(centre.lng, 9),
    area,
    perimeter,
    boundary: geometry ? JSON.stringify(geometry) : null,
    address: place.address || '',
    pincode: place.pincode || '',
    state: place.state || '',
    district: place.district || '',
    city: place.city || '',
    ward: place.ward || '',
  }
}
