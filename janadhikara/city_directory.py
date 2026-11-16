"""Cities a Janadhikara site can serve. Picking one in App Setting > City fills in the city code, state and
the map's opening view and limits, so nothing is typed by hand. Bounds are (south, west, north, east) boxes
around the city; add a city by adding a line here and its name to the City Name options of App Setting."""

import json
import os

import frappe

# name: (code, state, centre lat, centre lng, zoom, south, west, north, east)
_CITIES = {
	"Guwahati": ("guwahati", "Assam", 26.1445, 91.7362, 12, 25.95, 91.45, 26.35, 92.05),
	"Hyderabad": ("hyderabad", "Telangana", 17.3850, 78.4867, 11, 17.15, 78.15, 17.70, 78.75),
	"Bengaluru": ("bengaluru", "Karnataka", 12.9716, 77.5946, 11, 12.75, 77.35, 13.20, 77.85),
	"Chennai": ("chennai", "Tamil Nadu", 13.0827, 80.2707, 11, 12.85, 80.05, 13.30, 80.45),
	"Delhi": ("delhi", "Delhi", 28.6139, 77.2090, 11, 28.35, 76.80, 28.90, 77.45),
	"Kolkata": ("kolkata", "West Bengal", 22.5726, 88.3639, 11, 22.35, 88.15, 22.85, 88.60),
	"Mumbai": ("mumbai", "Maharashtra", 19.0760, 72.8777, 11, 18.85, 72.70, 19.35, 73.15),
	"Pune": ("pune", "Maharashtra", 18.5204, 73.8567, 11, 18.30, 73.60, 18.75, 74.10),
	"Ahmedabad": ("ahmedabad", "Gujarat", 23.0225, 72.5714, 11, 22.85, 72.35, 23.25, 72.80),
	"Jaipur": ("jaipur", "Rajasthan", 26.9124, 75.7873, 11, 26.70, 75.55, 27.10, 76.05),
	"Lucknow": ("lucknow", "Uttar Pradesh", 26.8467, 80.9462, 11, 26.65, 80.75, 27.05, 81.15),
	"Bhubaneswar": ("bhubaneswar", "Odisha", 20.2961, 85.8245, 12, 20.15, 85.65, 20.45, 86.00),
	"Patna": ("patna", "Bihar", 25.5941, 85.1376, 11, 25.40, 84.90, 25.80, 85.40),
	"Shillong": ("shillong", "Meghalaya", 25.5788, 91.8933, 12, 25.45, 91.75, 25.70, 92.05),
}

CITY_NAMES = list(_CITIES)


def get_city(name):
	"""Everything the app needs to know about a city, or None when it is not in the directory."""
	row = _CITIES.get(name)
	if not row:
		return None
	code, state, lat, lng, zoom, south, west, north, east = row
	return {
		"name": name, "code": code, "state": state,
		"map_center": [lat, lng], "map_zoom": zoom,
		"map_bounds": [[south, west], [north, east]],
	}


BOUNDARY_DIR = os.path.join(os.path.dirname(__file__), "city_boundaries")


def get_boundary(code):
	"""The city's outline as GeoJSON from city_boundaries/<code>.json (OpenStreetMap municipal boundary,
	simplified), or None when none has been added for that city yet."""
	path = os.path.join(BOUNDARY_DIR, f"{code}.json")
	if not os.path.isfile(path):
		return None
	with open(path) as f:
		return json.load(f)


@frappe.whitelist()
def get_city_details(name):
	"""A city's code, state, map view and (when available) outline, for the App Setting form's map."""
	city = get_city(name)
	if city:
		city["boundary"] = get_boundary(city["code"])
	return city
