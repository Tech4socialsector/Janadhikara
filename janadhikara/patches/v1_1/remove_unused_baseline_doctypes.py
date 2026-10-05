import frappe

UNUSED = ("Survey Field Unit",)


def execute():
	"""Survey Field Unit is no longer part of the app:
	take them out of the Baseline sidebar, drop their AI policies, and delete
	the doctypes (with any data) if they still exist."""
	for item in frappe.get_all("App Module DocType Item", filters={"doctype_name": ["in", UNUSED]}, pluck="name"):
		frappe.delete_doc("App Module DocType Item", item, force=True, ignore_permissions=True)

	for doctype in UNUSED:
		if frappe.db.exists("AI Data Policy", doctype):
			frappe.delete_doc("AI Data Policy", doctype, force=True, ignore_permissions=True)
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
	frappe.db.commit()
