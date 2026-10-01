"""Registry of the built-in field functions a "Field Function Mapping" rule
can tag onto a field.

A function is something the Vue app runs when a field changes (e.g. capturing
a drawn map shape) and that produces several named outputs (latitude, area,
pincode ...). A rule says: "when <trigger field> on <doctype> fires this
function, write output X into field A, output Y into field B ...".

To add a function:
  1. Add an entry to FIELD_FUNCTIONS below (description, which trigger field
     types it accepts, and its outputs with the field types each can fill).
  2. Add its name to the `function_name` Select options, and any new output
     keys to the `output` Select options of Field Function Mapping Item
     (test_field_function_mapping.py fails if these drift from this file).
  3. Implement it in frontend/src/utils/fieldFunctions.js under the same name.
"""

NUMBER = ["Float", "Int", "Decimal", "Currency", "Data"]
TEXT = ["Data", "Small Text", "Text", "Long Text"]
LINK_OR_TEXT = ["Link", "Data"]

FIELD_FUNCTIONS = {
	"Geo Shape Capture": {
		"description": (
			"Runs when something is drawn, edited or deleted on a Geolocation map "
			"(line, polygon, rectangle or circle). Works out the shape's centre point, "
			"boundary polygon, area (sq m) and perimeter (m), and looks up the address, "
			"pincode, state, district, city and ward of its centre."
		),
		"trigger_fieldtypes": ["Geolocation"],
		"outputs": {
			"latitude": {"label": "Latitude (centre point)", "fieldtypes": NUMBER},
			"longitude": {"label": "Longitude (centre point)", "fieldtypes": NUMBER},
			"boundary": {"label": "Boundary polygon (GeoJSON)", "fieldtypes": ["JSON", "Long Text", "Text", "Code"]},
			"area": {"label": "Area (square metres)", "fieldtypes": NUMBER},
			"perimeter": {"label": "Perimeter (metres)", "fieldtypes": NUMBER},
			"captured_by": {"label": "Captured by (current user)", "fieldtypes": ["Link", "Data"]},
			"captured_on": {"label": "Captured on (now)", "fieldtypes": ["Datetime", "Data"]},
			"address": {"label": "Address of the centre point", "fieldtypes": TEXT},
			"pincode": {"label": "Pincode", "fieldtypes": LINK_OR_TEXT},
			"state": {"label": "State", "fieldtypes": LINK_OR_TEXT},
			"district": {"label": "District", "fieldtypes": LINK_OR_TEXT},
			"city": {"label": "City", "fieldtypes": LINK_OR_TEXT},
			"ward": {"label": "Ward", "fieldtypes": LINK_OR_TEXT},
		},
	},
	"Distance Between Points": {
		"description": (
			"Runs when either map field changes. Measures the straight-line distance between "
			"the centre of the trigger map field and the centre of a second map field "
			"(set per row as 'Also Uses Field'), e.g. settlement to nearest health centre."
		),
		"trigger_fieldtypes": ["Geolocation"],
		# Each mapping row must name this extra field, and it must be one of these types.
		"input_fieldtypes": ["Geolocation"],
		"outputs": {
			"distance_m": {"label": "Distance (metres)", "fieldtypes": NUMBER},
			"distance_km": {"label": "Distance (kilometres)", "fieldtypes": NUMBER},
		},
	},
}


def all_output_keys():
	keys = []
	for func in FIELD_FUNCTIONS.values():
		for key in func["outputs"]:
			if key not in keys:
				keys.append(key)
	return keys
