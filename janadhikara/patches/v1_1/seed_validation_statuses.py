import frappe


def execute():
	"""Validation Status became a master (it was a fixed list on Household Profile). Create the two
	options the old list had - open to everyone - so existing households stay valid. Roles are then
	set per option from the Validation Status list."""
	for name in ("Revision Needed", "Validated"):
		if not frappe.db.exists("Validation Status", name):
			frappe.get_doc({"doctype": "Validation Status", "status_name": name, "enabled": 1}).insert(
				ignore_permissions=True
			)
	frappe.db.commit()
