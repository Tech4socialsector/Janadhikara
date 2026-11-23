import frappe

# three identical one-field tables (role -> Role) are replaced by Frappe's own "Has Role"
OLD = ("App Module Setting Role", "App Module Group Role", "Announcement Target Role")


def execute():
	"""Carry the rows of the three duplicate role tables over to Has Role (same parent, parent type and field), then
	delete the duplicates' doctypes and tables."""
	for old in OLD:
		if not frappe.db.table_exists(old):
			continue
		for row in frappe.get_all(old, fields=["name", "creation", "modified", "modified_by", "owner", "idx", "role", "parent", "parentfield", "parenttype"]):
			if frappe.db.exists("Has Role", {"parent": row.parent, "parenttype": row.parenttype, "parentfield": row.parentfield, "role": row.role}):
				continue
			frappe.get_doc({"doctype": "Has Role", "role": row.role, "idx": row.idx, "parent": row.parent, "parenttype": row.parenttype, "parentfield": row.parentfield, "creation": row.creation, "modified": row.modified, "owner": row.owner, "modified_by": row.modified_by}).db_insert()
		if frappe.db.exists("DocType", old):
			frappe.delete_doc("DocType", old, force=True, ignore_permissions=True)
		frappe.db.sql_ddl(f"drop table if exists `tab{old}`")
	frappe.db.commit()
