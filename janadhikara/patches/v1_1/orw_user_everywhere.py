import frappe


def execute():
	"""Name of the ORW is a User link on the Settlement and Individual Profile too (as on the Household Profile).
	A Settlement that held the ORW's typed name gets the matching user (by full name or email), otherwise the user
	who created the record; an Individual Profile without one gets the user who created it."""
	for doctype in ("Settlement", "Individual Profile"):
		if not frappe.db.has_column(doctype, "orw_name"):
			continue
		rows = frappe.db.sql(
			f"select name, owner, orw_name from `tab{doctype}` where ifnull(orw_name, '') = '' or orw_name not like '%%@%%'",
			as_dict=True,
		)
		for row in rows:
			user = None
			if row.orw_name:
				user = frappe.db.get_value("User", {"full_name": row.orw_name}, "name") or (
					row.orw_name if frappe.db.exists("User", row.orw_name) else None
				)
			user = user or (row.owner if frappe.db.exists("User", row.owner) else None)
			frappe.db.set_value(doctype, row.name, "orw_name", user, update_modified=False)
	frappe.db.delete("Translation", {"context": ["like", "janadhikara:field:Settlement:orw_name:%"]})
	frappe.db.commit()
