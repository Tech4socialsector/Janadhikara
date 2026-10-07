import frappe

# The dashboard counts a profile on its Date: existing profiles get the day they were created.


def execute():
	if frappe.db.has_column("Individual Profile", "record_date"):
		frappe.db.sql("update `tabIndividual Profile` set record_date = date(creation) where record_date is null")
		frappe.db.commit()
