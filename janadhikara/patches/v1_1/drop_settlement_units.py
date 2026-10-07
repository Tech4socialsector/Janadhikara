import frappe

# Settlement no longer has intervention units, employees, boundary, status or
# address breakdown fields: remove the map-capture rules that still point at them.
GONE = ("Settlement Intervention Unit", "Settlement Unit Employee")


def execute():
	for rule in frappe.get_all("Field Function Mapping", filters={"target_doctype": ["in", GONE]}, pluck="name"):
		frappe.delete_doc("Field Function Mapping", rule, force=1, ignore_permissions=True)
	for dt in GONE:
		if frappe.db.exists("AI Data Policy", dt):
			frappe.delete_doc("AI Data Policy", dt, force=1, ignore_permissions=True)
	kept = {"latitude", "longitude", "boundary_area", "boundary_perimeter", "q19_1_location_details_settlement", "q3_ward_no_city_corporation"}
	for rule in frappe.get_all("Field Function Mapping", filters={"target_doctype": "Settlement"}, pluck="name"):
		doc = frappe.get_doc("Field Function Mapping", rule)
		doc.field_mappings = [row for row in doc.field_mappings if row.target_field in kept]
		doc.save(ignore_permissions=True)
	frappe.db.commit()
