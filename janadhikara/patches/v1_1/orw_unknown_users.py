import frappe


def execute():
	"""A Name of the ORW that points at a user who no longer exists (a deleted account) stops the record from saving:
	clear it, and the next save fills it with the signed-in user."""
	for doctype, field in (("Settlement", "orw_name"), ("Individual Profile", "orw_name"), ("Household Profile", "assigned_worker")):
		if frappe.db.has_column(doctype, field):
			frappe.db.sql(
				f"""update `tab{doctype}` set `{field}` = null
				where ifnull(`{field}`, '') != '' and `{field}` not in (select name from `tabUser`)"""
			)
	frappe.db.commit()
