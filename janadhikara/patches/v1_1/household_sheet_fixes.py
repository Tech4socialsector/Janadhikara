import frappe

# Household Profile follows the sheet exactly: Q69 has two options, and Q33 lists only the districts of Assam.


def execute():
	frappe.db.sql("update `tabHousehold Profile` set status = 'Partially Completed' where status not in ('Completed', 'Partially Completed')")
	if frappe.db.exists("Assam District", "Outside Assam") and not frappe.db.exists("Household Profile", {"allotted_where": "Outside Assam"}):
		frappe.delete_doc("Assam District", "Outside Assam", force=1, ignore_permissions=True)
	frappe.db.commit()
