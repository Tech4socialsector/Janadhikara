// Built-in field functions, keyed by the exact name used in the Field
// Function Mapping doctype's "Function" option (and in
// janadhikara/field_functions.py, which holds each function's description
// and allowed outputs/field types - keep the three in step).
//
// A function is `{ run, hierarchy?, summary? }`:
//   run(value, ctx)  -> async; returns { outputKey: value, ... }.
//                       `value` is the trigger field's value; ctx has { user,
//                       inputValue } - inputValue is the value of the rule's
//                       "Also Uses Field" (for functions that read a second field)
//   hierarchy        -> for outputs that are Link fields to master data,
//                       which other output narrows them ({ district: 'state' }
//                       means "look District up within the State just found")
//   summary(outputs) -> optional one-line toast text after a successful run
//
// To add a function: implement it here, then register it in
// field_functions.py and the doctype's Select options (see that file).
import { describeGeoValue, collectionCentroid, distanceBetweenM } from '@/utils/geo'

function nowString() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export const FIELD_FUNCTIONS = {
  // Fired by the map field's 'geo-changed' event - value is the GeoJSON of
  // everything drawn (null once it's all deleted).
  'Geo Shape Capture': {
    async run(value, ctx) {
      if (!value) {
        // Everything was deleted: clear the shape-derived numbers/boundary,
        // but leave the address parts alone (someone may have edited them).
        return { boundary: null, area: 0, perimeter: 0 }
      }
      const details = await describeGeoValue(value)
      if (!details) return {}
      return {
        latitude: details.latitude,
        longitude: details.longitude,
        boundary: details.boundary,
        area: details.area,
        perimeter: details.perimeter,
        ...(details.boundary ? { captured_by: ctx.user, captured_on: nowString() } : {}),
        address: details.address,
        pincode: details.pincode,
        state: details.state,
        district: details.district,
        city: details.city,
        ward: details.ward,
      }
    },
    hierarchy: { district: 'state', city: 'district', ward: 'city' },
    summary(out) {
      const bits = []
      if (out.area) bits.push(`${Math.round(out.area).toLocaleString()} sq m`)
      if (out.perimeter) bits.push(`${Math.round(out.perimeter).toLocaleString()} m perimeter`)
      return bits.length ? `Captured: ${bits.join(', ')}` : ''
    },
  },

  // Fired when either map field changes - `value` is the trigger field's
  // GeoJSON and ctx.inputValue the other map field's. Distance is centre to
  // centre; if either map is empty the distances are cleared.
  'Distance Between Points': {
    async run(value, ctx) {
      const metres = distanceBetweenM(collectionCentroid(value), collectionCentroid(ctx.inputValue))
      if (metres === null) return { distance_m: null, distance_km: null }
      return {
        distance_m: Math.round(metres * 100) / 100,
        distance_km: Math.round(metres / 10) / 100,
      }
    },
    summary(out) {
      return out.distance_km != null ? `Distance: ${out.distance_km.toLocaleString()} km` : ''
    },
  },
}
