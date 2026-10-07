import frappe

# The AI assistant may read but never change which partner or settlement a household belongs to.
RULES = {
	"partner_organization": "controls who can see the record",
	"settlement": "controls who can see the record",
}


def execute():
	if not frappe.db.exists("AI Data Policy", "Household Profile"):
		return
	doc = frappe.get_doc("AI Data Policy", "Household Profile")
	have = {row.policy_field: row for row in doc.field_rules}
	for field, reason in RULES.items():
		if field in have:
			have[field].handling = "Read Only"
		else:
			doc.append("field_rules", {"policy_field": field, "handling": "Read Only", "reason": reason})
	doc.save(ignore_permissions=True)
	frappe.db.commit()
