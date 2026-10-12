import frappe


def execute():
	"""Data Collector (an Employee link) became Name of the ORW (a User link): carry the saved values over and
	drop the old label's translations (the new ones are imported on migrate)."""
	rows = frappe.db.sql(
		"select name, assigned_worker from `tabHousehold Profile` where ifnull(assigned_worker, '') != ''", as_dict=True
	)
	for row in rows:
		if frappe.db.exists("User", row.assigned_worker):
			continue
		user, email = frappe.db.get_value("Employee", row.assigned_worker, ["user", "email"]) or (None, None)
		user = user or (email if email and frappe.db.exists("User", email) else None)
		frappe.db.set_value("Household Profile", row.name, "assigned_worker", user, update_modified=False)
	frappe.db.delete(
		"Translation",
		{"context": ["like", "janadhikara:field:Household Profile:assigned_worker:%"]},
	)
