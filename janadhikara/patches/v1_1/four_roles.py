import frappe

from janadhikara.statuses import COORDINATORS, STATUSES


def execute():
	"""The app runs on four roles for now: ORW, Program Coordinator, Program Manager and Organization Admin.
	Data Collector becomes ORW (users and workers keep it), and Revision Needed / Validated are open to the
	three coordinator roles."""
	if frappe.db.exists("Role", "Data Collector") and not frappe.db.exists("Role", "ORW"):
		frappe.rename_doc("Role", "Data Collector", "ORW", force=True)
	elif frappe.db.exists("Role", "Data Collector"):
		# ORW already exists: move the people over
		frappe.db.sql("update `tabHas Role` set role = 'ORW' where role = 'Data Collector'")
	frappe.db.sql("update `tabEmployee` set role = 'ORW' where role = 'Data Collector'")

	for name, roles in STATUSES.items():
		if not roles or not frappe.db.exists("Validation Status", name):
			continue
		doc = frappe.get_doc("Validation Status", name)
		doc.set("roles", [{"role": r} for r in COORDINATORS if frappe.db.exists("Role", r)])
		doc.save(ignore_permissions=True)
	frappe.db.commit()
