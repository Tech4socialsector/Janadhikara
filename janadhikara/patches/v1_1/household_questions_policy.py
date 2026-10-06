import frappe


def execute():
	"""Household Profile can now hold Question Bank answers (a Question Answer table). Keep the
	answers away from the AI assistant, like the other confidential details. Rules for fields that
	no longer exist (the respondent contact is now "contact_number") are dropped, and the
	contact number is kept hidden."""
	if not frappe.db.exists("AI Data Policy", "Household Profile"):
		return
	policy = frappe.get_doc("AI Data Policy", "Household Profile")
	meta = frappe.get_meta("Household Profile")
	policy.field_rules = [r for r in policy.field_rules if meta.has_field(r.policy_field)]
	have = {r.policy_field for r in policy.field_rules}
	for field, reason in (("question_answers", "questionnaire answers"), ("contact_number", "contact number")):
		if meta.has_field(field) and field not in have:
			policy.append("field_rules", {"policy_field": field, "handling": "Hidden", "reason": reason})
	policy.save(ignore_permissions=True)
	frappe.db.commit()
