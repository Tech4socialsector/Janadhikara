import frappe

DOCTYPES = ("Settlement", "Household Profile", "Individual Profile", "Survey")


def execute():
	"""New `record_date` (defaults to today). Records that already existed get
	the day they were created."""
	for doctype in DOCTYPES:
		if frappe.db.has_column(doctype, "record_date"):
			frappe.db.sql(
				f"update `tab{doctype}` set record_date = date(creation) where record_date is null"
			)
	frappe.db.commit()
