import frappe


def execute():
	"""The Hyderabad roster's Sex now uses the Individual Profile's options (Others, not Other)."""
	if frappe.db.table_exists("HYD Household Member"):
		frappe.db.sql("update `tabHYD Household Member` set gender = 'Others' where gender = 'Other'")
