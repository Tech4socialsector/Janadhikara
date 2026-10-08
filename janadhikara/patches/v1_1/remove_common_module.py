import frappe


def execute():
	"""The Common module held nothing; drop its Module Def so it stops showing in Desk."""
	if frappe.db.exists("Module Def", "Common") and not frappe.db.exists("DocType", {"module": "Common"}):
		frappe.delete_doc("Module Def", "Common", ignore_permissions=True, force=True)
