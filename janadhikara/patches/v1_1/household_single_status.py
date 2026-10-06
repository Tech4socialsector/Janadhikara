import frappe


def execute():
	"""Household Profile had "Documentation Status" (Completed / Partially Completed) next to
	"Status" - the same thing twice. Only Status is kept. A household still at Draft or In
	Progress takes what its documentation status said: Completed -> Completed,
	Partially Completed -> In Progress. (Revision Needed / Validated are never overwritten.)"""
	if not frappe.db.has_column("Household Profile", "documentation_status"):
		return
	frappe.db.sql(
		"""update `tabHousehold Profile` set status = 'Completed'
		where documentation_status = 'Completed' and status in ('Draft', 'In Progress')"""
	)
	frappe.db.sql(
		"""update `tabHousehold Profile` set status = 'In Progress'
		where documentation_status = 'Partially Completed' and status = 'Draft'"""
	)
	if frappe.db.exists("AI Data Policy", "Household Profile"):
		policy = frappe.get_doc("AI Data Policy", "Household Profile")
		meta = frappe.get_meta("Household Profile")
		policy.field_rules = [r for r in policy.field_rules if meta.has_field(r.policy_field)]
		policy.save(ignore_permissions=True)
	frappe.db.commit()
