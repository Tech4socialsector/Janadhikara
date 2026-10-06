import frappe


def execute():
	"""Household Profile had two fields for the same person: Assigned Worker (an Employee) and
	Data Collector (the User who created it). Only Assigned Worker is kept, labelled "Data
	Collector". Households that only had the old user field get the matching worker, and the
	AI policy forgets the removed fields."""
	if frappe.db.has_column("Household Profile", "surveyor"):
		rows = frappe.db.sql(
			"""select name, surveyor from `tabHousehold Profile`
			where ifnull(assigned_worker, '') = '' and ifnull(surveyor, '') != ''""",
			as_dict=True,
		)
		for row in rows:
			employee = frappe.db.get_value(
				"Employee", {"parenttype": "Partner Details", "user": row.surveyor}, "name"
			) or frappe.db.get_value("Employee", {"parenttype": "Partner Details", "email": row.surveyor}, "name")
			if employee:
				frappe.db.set_value("Household Profile", row.name, "assigned_worker", employee, update_modified=False)

	if frappe.db.exists("AI Data Policy", "Household Profile"):
		policy = frappe.get_doc("AI Data Policy", "Household Profile")
		meta = frappe.get_meta("Household Profile")
		policy.field_rules = [r for r in policy.field_rules if meta.has_field(r.policy_field)]
		if not any(r.policy_field == "assigned_worker" for r in policy.field_rules):
			policy.append(
				"field_rules",
				{"policy_field": "assigned_worker", "handling": "Read Only", "reason": "set from the signed-in user"},
			)
		policy.save(ignore_permissions=True)
	frappe.db.commit()
