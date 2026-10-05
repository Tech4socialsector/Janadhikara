import frappe


def execute():
	"""Household Member is now called Individual Profile. Runs before the doctype
	files are synced, so the renamed doctype keeps its table and data. The empty
	placeholder Individual Profile that used to exist (a different doctype) is
	dropped first so the name is free."""
	if not frappe.db.exists("DocType", "Household Member"):
		return
	if frappe.db.exists("DocType", "Individual Profile"):
		frappe.delete_doc("DocType", "Individual Profile", force=True, ignore_permissions=True)
		frappe.db.sql_ddl("drop table if exists `tabIndividual Profile`")

	frappe.flags.in_patch = True  # no file moves - the files are already renamed
	previous = frappe.conf.get("developer_mode")
	frappe.conf.developer_mode = 1  # DocType renames are only allowed in developer mode
	try:
		frappe.rename_doc("DocType", "Household Member", "Individual Profile", force=True)
	finally:
		frappe.conf.developer_mode = previous

	# The AI Data Policy is named after its doctype - keep that true.
	if frappe.db.exists("AI Data Policy", "Household Member") and not frappe.db.exists("AI Data Policy", "Individual Profile"):
		frappe.rename_doc("AI Data Policy", "Household Member", "Individual Profile", force=True)

	for item in frappe.get_all("App Module DocType Item", filters={"doctype_name": "Individual Profile"}, pluck="name"):
		frappe.db.set_value("App Module DocType Item", item, "label", "Individual Profile")
	frappe.db.commit()
