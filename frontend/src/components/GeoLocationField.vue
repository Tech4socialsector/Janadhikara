<template>
  <div>
    <div class="mb-1.5 flex items-center justify-between">
      <label class="text-sm text-gray-700 dark:text-gray-300">{{ field.label }}</label>
      <Tooltip v-if="hasShapes" text="Clear everything on the map">
        <Button variant="ghost" size="sm" icon="x" @click="clearLocation" />
      </Tooltip>
    </div>

    <div
      class="relative isolate h-96 w-full overflow-hidden rounded-lg border dark:border-gray-800"
    >
      <div ref="mapEl" class="h-full w-full" />
    </div>

    <p v-if="locateError" class="mt-1.5 text-xs text-red-500">{{ locateError }}</p>
    <p v-if="resolvingAddress" class="mt-1.5 text-p-xs text-ink-gray-5">
      Looking up address...
    </p>
    <p v-else class="mt-1.5 text-p-xs text-ink-gray-5">
      {{ field.description || 'Click the map to drop a pin, or use the toolbar to draw lines, shapes and circles.' }}
    </p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { FeatherIcon, Tooltip, Button } from 'frappe-ui'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import { reverseGeocode } from '@/utils/geo'
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'

// Leaflet's default marker icon paths are baked in relative to its own CSS
// origin, which breaks under Vite's asset hashing - point them at the
// actual bundled URLs instead.
L.Icon.Default.mergeOptions({
  iconUrl: markerIconUrl,
  iconRetinaUrl: markerIcon2xUrl,
  shadowUrl: markerShadowUrl,
})

// Same map defaults, base layers and overlays as Frappe desk's own
// Geolocation control (see frappe/utils map_defaults), so a field looks and
// behaves the same in both places.
const DEFAULT_CENTER = [19.08, 72.8961]
const DEFAULT_ZOOM = 5
const PIN_ZOOM = 15
const TILES = {
  street: {
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: { attribution: '&copy; OpenStreetMap contributors' },
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    options: { attribution: '&copy; Esri &copy; OpenStreetMap contributors' },
  },
  labels: {
    url: 'https://tiles.stadiamaps.com/tiles/stamen_toner_labels/{z}/{x}/{y}{r}.png',
    options: { attribution: '&copy; Stadia Maps &copy; Stamen Design &copy; OpenMapTiles' },
  },
  terrain: {
    url: 'https://tiles.stadiamaps.com/tiles/stamen_terrain_lines/{z}/{x}/{y}{r}.png',
    options: { attribution: '&copy; Stadia Maps &copy; Stamen Design &copy; OpenMapTiles' },
  },
}

// Circles and circle markers are plain Points in GeoJSON - desk keeps their
// radius/type in `properties` so they round-trip. Patched once, globally
// (Leaflet classes are shared), exactly as desk's own control does.
let geoJsonPatched = false
function patchGeoJSON() {
  if (geoJsonPatched) return
  geoJsonPatched = true
  const pointToGeoJSON = L.Circle.prototype.toGeoJSON
  L.Circle.include({
    toGeoJSON() {
      const feature = pointToGeoJSON.call(this)
      feature.properties = { point_type: 'circle', radius: this.getRadius() }
      return feature
    },
  })
  L.CircleMarker.include({
    toGeoJSON() {
      const feature = pointToGeoJSON.call(this)
      feature.properties = { point_type: 'circlemarker', radius: this.getRadius() }
      return feature
    },
  })
}

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null },
})
const emit = defineEmits(['update:modelValue', 'address-resolved', 'pincode-resolved', 'location-resolved', 'geo-changed'])

const mapEl = ref(null)
const locating = ref(false)
const locateError = ref('')
const resolvingAddress = ref(false)
const hasShapes = ref(false)
let map = null
let drawnItems = null
let drawControl = null
let interacting = false // a draw/edit/delete tool is active - clicks belong to it
let lastValue = null // last serialized value we emitted or loaded
let locateEl = null
let hadShapes = false // drawn (non-pin) shapes present at the last commit

// Reverse-geocodes via OpenStreetMap's Nominatim (same OSM data source as
// the tile layer, free and keyless) so a dropped pin also fills in a real,
// human-readable address (and a Pincode when Nominatim returns one).
// Only called from pin actions (click/drag/"use my location"), not from
// loading an existing value, so opening a saved record never overwrites
// values someone already typed by hand.
async function resolveAddress(lat, lng) {
  resolvingAddress.value = true
  try {
    const place = await reverseGeocode(lat, lng)
    if (place?.address) emit('address-resolved', place.address)
    if (place?.pincode) emit('pincode-resolved', place.pincode)
  } finally {
    resolvingAddress.value = false
  }
}

function pointToLayer(feature, latlng) {
  const type = feature.properties?.point_type
  if (type === 'circle') return L.circle(latlng, { radius: feature.properties.radius })
  if (type === 'circlemarker') return L.circleMarker(latlng, { radius: feature.properties.radius })
  return L.marker(latlng)
}

// Leaflet layer groups nest (geoJSON returns a group of groups) - flatten to
// individual layers so drawnItems holds one layer per shape, which is what
// the edit/delete tools operate on.
function addFlat(source, target) {
  if (source instanceof L.LayerGroup) source.eachLayer((l) => addFlat(l, target))
  else target.addLayer(source)
}

function serialize() {
  if (!drawnItems || drawnItems.getLayers().length === 0) return null
  return JSON.stringify(drawnItems.toGeoJSON())
}

function refreshShapeState() {
  hasShapes.value = !!drawnItems && drawnItems.getLayers().length > 0
}

function commit() {
  refreshShapeState()
  lastValue = serialize()
  emit('update:modelValue', lastValue)
  // Anything on the map - a pin or a drawn shape - also announces itself as
  // 'geo-changed', so Field Function Mapping rules can derive centre point,
  // boundary, area, perimeter and the address breakdown from it (see
  // useFieldFunctions). The older location-resolved/address-resolved events
  // still fire for a pin, for forms that opt in via geo_* field options;
  // reverseGeocode() caches, so both together cost one lookup.
  const nowShapes = !!drawnItems && drawnItems.getLayers().length > 0
  if (nowShapes) emit('geo-changed', lastValue)
  else if (hadShapes) emit('geo-changed', null)
  hadShapes = nowShapes
}

function isPin(layer) {
  return layer instanceof L.Marker
}

function pinLayer() {
  let found = null
  drawnItems.eachLayer((l) => {
    if (!found && isPin(l)) found = l
  })
  return found
}

function hasNonPinShapes() {
  let any = false
  drawnItems.eachLayer((l) => {
    if (!isPin(l)) any = true
  })
  return any
}

function onPinMoved(layer) {
  const { lat, lng } = layer.getLatLng()
  commit()
  if (layer === pinLayer()) {
    emit('location-resolved', { lat, lng })
    resolveAddress(lat, lng)
  }
}

function watchMarker(layer) {
  layer.on('dragend', () => onPinMoved(layer))
}

function loadValue(value) {
  drawnItems.clearLayers()
  lastValue = null
  if (value) {
    try {
      const geojson = typeof value === 'string' ? JSON.parse(value) : value
      addFlat(L.geoJSON(geojson, { pointToLayer }), drawnItems)
      lastValue = typeof value === 'string' ? value : JSON.stringify(value)
    } catch {
      // not valid GeoJSON - treat as unset
    }
  }
  drawnItems.eachLayer((l) => {
    if (isPin(l)) {
      l.dragging?.enable()
      watchMarker(l)
    }
  })
  refreshShapeState()
}

function fitToShapes() {
  if (!map || !drawnItems || drawnItems.getLayers().length === 0) return
  try {
    map.invalidateSize()
    const layers = drawnItems.getLayers()
    if (layers.length === 1 && isPin(layers[0])) {
      map.setView(layers[0].getLatLng(), PIN_ZOOM)
    } else {
      map.fitBounds(drawnItems.getBounds(), { padding: [40, 40] })
    }
  } catch {
    // a zero-area bounds can throw - the default view is fine then
  }
}

function setPin(lat, lng) {
  let layer = pinLayer()
  if (layer) {
    layer.setLatLng([lat, lng])
  } else {
    layer = L.marker([lat, lng], { draggable: true })
    drawnItems.addLayer(layer)
    watchMarker(layer)
  }
  map.setView([lat, lng], Math.max(map.getZoom(), PIN_ZOOM))
  onPinMoved(layer)
}

function clearLocation() {
  drawnItems?.clearLayers()
  commit()
}

function captureLocation() {
  if (!navigator.geolocation) {
    locateError.value = 'Geolocation is not supported by this browser.'
    return
  }
  locating.value = true
  locateEl?.classList.add('geo-locating')
  locateError.value = ''
  navigator.geolocation.getCurrentPosition(
    (position) => {
      locating.value = false
      locateEl?.classList.remove('geo-locating')
      setPin(position.coords.latitude, position.coords.longitude)
    },
    (err) => {
      locating.value = false
      locateEl?.classList.remove('geo-locating')
      locateError.value = err.message || 'Could not get your location.'
    },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

// Only react to external value changes (e.g. loading an existing record) -
// commit() already keeps the emitted value in sync for edits made through
// the map itself, so this must not fight that.
watch(
  () => props.modelValue,
  (value) => {
    if (!map) return
    const incoming = value || null
    if (incoming === lastValue) return
    loadValue(incoming)
    fitToShapes()
  },
)

onMounted(async () => {
  // leaflet-draw is a classic script that extends window.L - it has to be
  // loaded after window.L exists, hence the dynamic import. It also reads an
  // undeclared `type` global when measuring a polygon's area (a known bug
  // that throws under strict-mode bundles), so that is predeclared.
  window.L = L
  window.type = ''
  await import('leaflet-draw')
  if (!mapEl.value) return
  patchGeoJSON()

  map = L.map(mapEl.value).setView(DEFAULT_CENTER, DEFAULT_ZOOM)

  const street = L.tileLayer(TILES.street.url, TILES.street.options)
  const satellite = L.tileLayer(TILES.satellite.url, TILES.satellite.options)
  const labels = L.tileLayer(TILES.labels.url, TILES.labels.options)
  const terrain = L.tileLayer(TILES.terrain.url, TILES.terrain.options)
  street.addTo(map)
  L.control.layers({ Default: street, Satellite: satellite }, { Labels: labels, Terrain: terrain }).addTo(map)

  // "Use my location" as a real Leaflet control, stacked under the layer
  // switcher - so it gets the same size, margin and border as every other
  // control instead of being a hand-positioned overlay that drifts out of
  // line with them.
  const LocateControl = L.Control.extend({
    options: { position: 'topright' },
    onAdd() {
      const bar = L.DomUtil.create('div', 'leaflet-bar leaflet-control')
      const a = L.DomUtil.create('a', 'geo-locate-btn', bar)
      a.href = '#'
      a.title = 'Use my current location'
      a.setAttribute('role', 'button')
      a.setAttribute('aria-label', 'Use my current location')
      a.innerHTML =
        '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>'
      L.DomEvent.disableClickPropagation(bar)
      L.DomEvent.on(a, 'click', (e) => {
        L.DomEvent.preventDefault(e)
        captureLocation()
      })
      locateEl = a
      return bar
    },
  })
  map.addControl(new LocateControl())

  // Labels/Terrain only make sense over satellite imagery (same as desk).
  const setOverlayControl = (visible) => {
    const box = mapEl.value.querySelector('.leaflet-control-layers-overlays')
    const sep = mapEl.value.querySelector('.leaflet-control-layers-separator')
    if (box) box.style.display = visible ? '' : 'none'
    if (sep) sep.style.display = visible ? '' : 'none'
  }
  setOverlayControl(false)
  map.on('baselayerchange', (e) => {
    const isSatellite = e.name === 'Satellite'
    setOverlayControl(isSatellite)
    if (!isSatellite) {
      map.removeLayer(labels)
      map.removeLayer(terrain)
    }
  })

  drawnItems = new L.FeatureGroup().addTo(map)
  drawControl = new L.Control.Draw({
    position: 'topleft',
    draw: {
      polyline: { shapeOptions: { color: '#3b82f6', weight: 10 } },
      polygon: {
        allowIntersection: false,
        drawError: { color: '#f59e0b', message: "<strong>Oh snap!<strong> you can't draw that!" },
        shapeOptions: { color: '#3b82f6' },
      },
      circle: true,
      rectangle: { shapeOptions: { clickable: false } },
    },
    edit: { featureGroup: drawnItems, remove: true },
  })
  map.addControl(drawControl)

  map.on('draw:created', (e) => {
    if (e.layerType === 'marker') {
      e.layer.dragging?.enable()
      watchMarker(e.layer)
    }
    drawnItems.addLayer(e.layer)
    commit()
  })
  map.on('draw:edited draw:deleted', commit)
  ;['draw:drawstart', 'draw:editstart', 'draw:deletestart'].forEach((ev) =>
    map.on(ev, () => (interacting = true)),
  )
  // Released a tick late so the very click that finishes a shape isn't also
  // read as "drop a pin".
  ;['draw:drawstop', 'draw:editstop', 'draw:deletestop'].forEach((ev) =>
    map.on(ev, () => setTimeout(() => (interacting = false), 0)),
  )

  // A plain click drops/moves the single location pin - kept for forms that
  // capture where a household is. Skipped while a draw tool is active, and
  // once the map holds any drawn shape (a boundary), so clicking around a
  // polygon never adds stray pins.
  map.on('click', (e) => {
    if (interacting || hasNonPinShapes()) return
    setPin(e.latlng.lat, e.latlng.lng)
  })

  loadValue(props.modelValue || null)
  fitToShapes()

  // If the map's container hasn't finished its own layout yet when
  // L.map() measures it (e.g. it's still inside a CSS multi-column form
  // that reflows after mount), Leaflet bakes in the wrong size and the
  // view renders zoomed out to nearly the whole world - it never
  // self-corrects without an explicit invalidateSize(). Re-measuring on
  // the next frame and once more after a short delay covers slower reflows.
  requestAnimationFrame(() => {
    map?.invalidateSize()
    fitToShapes()
  })
  setTimeout(() => map?.invalidateSize(), 300)
})

onBeforeUnmount(() => {
  if (map) map.remove()
})
</script>

<style>
/* Tile seams: at fractional device-pixel ratios (browser zoom, HiDPI
scaling) Chrome leaves hairline gaps between tiles. A transparent outline
makes each tile cover its neighbours' edge pixels. */
.leaflet-container .leaflet-tile {
  outline: 1px solid transparent;
}
/* Leaflet's zoom/draw/layer/locate controls are plain <a> buttons - make
sure app-wide anchor/button resets don't shift their icons off-centre, and
the locate control matches their 30px size. */
.leaflet-container .leaflet-bar a,
.leaflet-container .leaflet-control-layers-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}
.leaflet-container .leaflet-bar a.geo-locate-btn {
  color: #374151;
  line-height: 1;
}
.leaflet-container .leaflet-bar a.geo-locate-btn.geo-locating svg {
  animation: geo-pulse 1s ease-in-out infinite;
  color: #2563eb;
}
@keyframes geo-pulse {
  50% {
    opacity: 0.35;
  }
}
/* leaflet-draw's toolbar icons are background sprites - keep them centred. */
.leaflet-draw-toolbar a {
  background-position: 50% 50%;
}
</style>
