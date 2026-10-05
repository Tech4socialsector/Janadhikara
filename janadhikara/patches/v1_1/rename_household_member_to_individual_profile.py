import frappe


def execute():
	"""Household Member is now called Individual Profile. Runs before the doctype
	files are synced, so the renamed doctype keeps its table and data.

	The empty placeholder Individual Profile that used to exist (a different
	doctype) is dropped first - with its AI Data Policy and sidebar entry, which
	would otherwise collide with the renamed doctype's own (the policy's
	target_doctype is unique). Safe to re-run."""
	if not frappe.db.exists("DocType", "Household Member"):
		return

	# 1. Clear out the old placeholder and everything that points at it.
	if frappe.db.exists("AI Data Policy", "Individual Profile"):
		frappe.delete_doc("AI Data Policy", "Individual Profile", force=True, ignore_permissions=True)
	for item in frappe.get_all("App Module DocType Item", filters={"doctype_name": "Individual Profile"}, pluck="name"):
		frappe.delete_doc("App Module DocType Item", item, force=True, ignore_permissions=True)
	if frappe.db.exists("DocType", "Individual Profile"):
		frappe.delete_doc("DocType", "Individual Profile", force=True, ignore_permissions=True)
	frappe.db.sql_ddl("drop table if exists `tabIndividual Profile`")

	# 2. Rename Household Member (table, data and every link to it follow).
	frappe.flags.in_patch = True  # no file moves - the files are already renamed
	previous = frappe.conf.get("developer_mode")
	frappe.conf.developer_mode = 1  # DocType renames are only allowed in developer mode
	try:
		frappe.rename_doc("DocType", "Household Member", "Individual Profile", force=True)
	finally:
		frappe.conf.developer_mode = previous

	# 3. Its AI Data Policy is named after its doctype - keep that true.
	if frappe.db.exists("AI Data Policy", "Household Member") and not frappe.db.exists("AI Data Policy", "Individual Profile"):
		frappe.db.set_value("AI Data Policy", "Household Member", "target_doctype", "Individual Profile", update_modified=False)
		frappe.rename_doc("AI Data Policy", "Household Member", "Individual Profile", force=True)

	for item in frappe.get_all("App Module DocType Item", filters={"doctype_name": "Individual Profile"}, pluck="name"):
		frappe.db.set_value("App Module DocType Item", item, "label", "Individual Profile")
	frappe.db.commit()
