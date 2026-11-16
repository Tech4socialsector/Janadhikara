// Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
// For license information, please see license.txt

// Shows the chosen city's urban area on a MapLibre GL vector map (free OpenFreeMap "Liberty" style, no key):
// roads, localities and neighbouring areas are labelled. The city's own outline (stored in the app under
// city_boundaries/, from OpenStreetMap - not the district) gets a red border and everything outside it is dimmed.
// A city with no stored outline gets its urban limits box (the limits the app's location fields use) instead.
const MAPLIBRE = "https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist";
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

frappe.ui.form.on("App Setting", {
	refresh(frm) {
		show_city_map(frm);
	},
	city_name(frm) {
		show_city_map(frm);
	},
});

function load_maplibre() {
	if (window.maplibregl) return Promise.resolve();
	if (!document.getElementById("maplibre-css")) {
		document.head.appendChild(
			Object.assign(document.createElement("link"), {
				id: "maplibre-css",
				rel: "stylesheet",
				href: `${MAPLIBRE}/maplibre-gl.css`,
			})
		);
	}
	return new Promise((resolve, reject) => {
		const script = Object.assign(document.createElement("script"), { src: `${MAPLIBRE}/maplibre-gl.js` });
		script.onload = resolve;
		script.onerror = reject;
		document.head.appendChild(script);
	});
}

function box_geojson(bounds) {
	const [[s, w], [n, e]] = bounds;
	return { type: "Polygon", coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] };
}

function pad_bounds(b) {
	const dx = (b.getEast() - b.getWest()) * 0.08;
	const dy = (b.getNorth() - b.getSouth()) * 0.08;
	return [[b.getWest() - dx, b.getSouth() - dy], [b.getEast() + dx, b.getNorth() + dy]];
}

function geojson_bounds(g) {
	const bounds = new maplibregl.LngLatBounds();
	const walk = (x) => (typeof x[0] === "number" ? bounds.extend(x) : x.forEach(walk));
	walk(g.coordinates);
	return bounds;
}

async function show_city_map(frm) {
	const city = frm.doc.city_name;
	const wrapper = frm.get_field("city_map").$wrapper;
	if (frm.city_map) {
		frm.city_map.remove();
		frm.city_map = null;
	}
	if (!city) {
		wrapper.html(`<p class="text-muted">${__("Choose a city to see its map.")}</p>`);
		return;
	}
	const c = await frappe.xcall("janadhikara.city_directory.get_city_details", { name: city });
	if (!c || city !== frm.doc.city_name) return;
	try {
		await load_maplibre();
	} catch (e) {
		wrapper.html(`<p class="text-muted">${__("The map could not be loaded.")}</p>`);
		return;
	}
	const box = box_geojson(c.map_bounds);
	const outline = c.boundary || box; // the city's stored outline, else its urban limits box
	if (city !== frm.doc.city_name) return;

	wrapper.html(`<div style="position:relative;height:max(560px,78vh);width:100%;border:1px solid #cfd4d9;border-radius:8px;overflow:hidden">
		<div class="city-map" style="position:absolute;inset:0"></div>
</div>`);
	let map;
	try {
		map = new maplibregl.Map({ container: wrapper.find(".city-map")[0], style: MAP_STYLE, bounds: geojson_bounds(outline), fitBoundsOptions: { padding: 60, maxZoom: 13 }, maxBounds: pad_bounds(geojson_bounds(box)), minZoom: 9, cooperativeGestures: true });
	} catch (e) {
		wrapper.html(`<p class="text-muted">${__("This browser cannot draw the map (WebGL is needed).")}</p>`);
		return;
	}
	frm.city_map = map;
	map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");
	map.on("load", () => {
		// Dim everything outside the city (the world with the city's outline cut out of it).
		const parts = outline.type === "Polygon" ? [outline.coordinates] : outline.coordinates;
		const world = [[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]];
		map.addSource("outside", { type: "geojson", data: { type: "Feature", geometry: { type: "Polygon", coordinates: [world, ...parts.map((p) => p[0])] } } });
		map.addSource("city", { type: "geojson", data: { type: "Feature", geometry: outline } });
		map.addLayer({ id: "outside-dim", type: "fill", source: "outside", paint: { "fill-color": "#1f2937", "fill-opacity": 0.3 } });
		map.addLayer({ id: "city-fill", type: "fill", source: "city", paint: { "fill-color": "#f06a60", "fill-opacity": 0.12 } });
		map.addLayer({ id: "city-line", type: "line", source: "city", layout: { "line-join": "round" }, paint: { "line-color": "#c2271d", "line-width": 3 } });
		const [lat, lng] = c.map_center;
		new maplibregl.Marker({ color: "#d6001c" })
			.setLngLat([lng, lat])
			.setPopup(new maplibregl.Popup({ offset: 24 }).setText(c.name))
			.addTo(map);
	});
}
