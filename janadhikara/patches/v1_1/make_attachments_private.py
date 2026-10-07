import frappe

# Photos and documents of households and people are personal data: files already uploaded as public
# (reachable without signing in) are made private. Frappe moves the file and updates the link.
DOCTYPES = ("Individual Profile", "Household Profile", "Settlement", "Settlement Street Photo", "Individual Document")


def execute():
	for name in frappe.get_all(
		"File", filters={"attached_to_doctype": ["in", DOCTYPES], "is_private": 0, "is_folder": 0}, pluck="name"
	):
		try:
			doc = frappe.get_doc("File", name)
			doc.is_private = 1
			doc.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"Could not make file {name} private")
	frappe.db.commit()
