import frappe


def execute():
	"""Household map capture: picking a point on a Household Profile's map
	fills its latitude, longitude and address. (Not the boundary - settlement
	and unit boundaries belong to the Settlement masters.)"""
	rule_name = "Household map capture"
	if frappe.db.exists("Field Function Mapping", rule_name):
		return
	frappe.get_doc({
		"doctype": "Field Function Mapping",
		"rule_name": rule_name,
		"enabled": 1,
		"function_name": "Geo Shape Capture",
		"target_doctype": "Household Profile",
		"trigger_field": "geo_location",
		"description": "Drop a pin on the household map and its coordinates and address are captured.",
		"field_mappings": [
			{"output": "latitude", "target_field": "latitude"},
			{"output": "longitude", "target_field": "longitude"},
			{"output": "address", "target_field": "address"},
		],
	}).insert(ignore_permissions=True)
	frappe.db.commit()
