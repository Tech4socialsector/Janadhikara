import frappe

# Field Function Mapping rules that reproduce what the map field used to do
# purely by field-name convention, now as editable records: drawing on a
# Settlement's Geo Location fills its centre point, address and ward.
RULES = [
	("Settlement", "Settlement map capture", "settlement_boundary"),
]


def execute():
	for doctype, rule_name, boundary_field in RULES:
		if frappe.db.exists("Field Function Mapping", rule_name):
			continue
		mappings = [
			("latitude", "latitude"),
			("longitude", "longitude"),
			("area", "boundary_area"),
			("perimeter", "boundary_perimeter"),
		]
		if doctype == "Settlement":
			mappings += [
				("address", "q19_1_location_details_settlement"),
				("ward", "q3_ward_no_city_corporation"),
			]
		frappe.get_doc({
			"doctype": "Field Function Mapping",
			"rule_name": rule_name,
			"enabled": 1,
			"function_name": "Geo Shape Capture",
			"target_doctype": doctype,
			"trigger_field": "geo_location",
			"description": "Draw or edit a shape on the map and the boundary details are captured automatically.",
			"field_mappings": [{"output": o, "target_field": t} for o, t in mappings],
		}).insert(ignore_permissions=True)
	frappe.db.commit()
