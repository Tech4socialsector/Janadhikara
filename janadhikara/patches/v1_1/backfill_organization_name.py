import frappe


def execute():
	"""Organization Name is fetched from the Partner Details when a record is saved; fill it in for the records
	that already exist, so lists, filters and exports show it too."""
	for doctype, link in (("Settlement", "partner_organization"), ("Household Profile", "partner_organization"), ("Individual Profile", "implementing_org")):
		if not frappe.db.has_column(doctype, "organization_name"):
			continue
		frappe.db.sql(
			f"""update `tab{doctype}` t join `tabPartner Details` p on p.name = t.`{link}`
			set t.organization_name = p.organization_name
			where ifnull(t.organization_name, '') = ''"""
		)
	frappe.db.commit()
