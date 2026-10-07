import frappe

# People's names may be shown to the AI assistant (phone numbers, addresses, positions and ID numbers
# stay hidden): remove the Hidden rules that were put on name fields.
NAME_FIELDS = {"member_name", "respondent_name", "household_head_name", "orw_name"}
HIDDEN_BY_DEFAULT = {"personal name", "personal detail", "personal detail (individual questionnaire)"}


def execute():
	for name in ("Household Profile", "Individual Profile", "Settlement"):
		if not frappe.db.exists("AI Data Policy", name):
			continue
		doc = frappe.get_doc("AI Data Policy", name)
		kept = [
			row for row in doc.field_rules
			if not (row.policy_field in NAME_FIELDS and row.handling == "Hidden" and (row.reason or "") in HIDDEN_BY_DEFAULT)
		]
		if len(kept) != len(doc.field_rules):
			doc.field_rules = kept
			doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.cache().delete_value("janadhikara_ai_policies")
