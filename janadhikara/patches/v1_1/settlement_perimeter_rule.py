import frappe

# The map-capture rule for Settlement also fills the area and perimeter of the drawn shape.
EXTRA = (("area", "boundary_area"), ("perimeter", "boundary_perimeter"))


def execute():
	for rule in frappe.get_all("Field Function Mapping", filters={"target_doctype": "Settlement"}, pluck="name"):
		doc = frappe.get_doc("Field Function Mapping", rule)
		have = {row.target_field for row in doc.field_mappings}
		for output, target in EXTRA:
			if target not in have:
				doc.append("field_mappings", {"output": output, "target_field": target})
		doc.save(ignore_permissions=True)
	frappe.db.commit()
