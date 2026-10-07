import frappe

# Individual Profile holds only the questions of the questionnaire sheet: drop AI policy rules for
# the removed consent, date, data-collector and comment fields.


def execute():
	if not frappe.db.exists("AI Data Policy", "Individual Profile"):
		return
	doc = frappe.get_doc("AI Data Policy", "Individual Profile")
	fields = {df.fieldname for df in frappe.get_meta("Individual Profile").fields}
	doc.field_rules = [row for row in doc.field_rules if row.policy_field in fields]
	doc.save(ignore_permissions=True)
	frappe.db.commit()
