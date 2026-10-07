import frappe

from janadhikara.ai.policy import SEED, ensure_policies


def execute():
	"""Individual Profile now follows the individual questionnaire (about 145 questions). The old
	education / health / entitlement / document tables and the occupation, income and relationship
	fields are gone. Bring its AI policy in line: every answer stays hidden from the assistant,
	and rules for fields that no longer exist are dropped."""
	ensure_policies()
	if not frappe.db.exists("AI Data Policy", "Individual Profile"):
		return
	policy = frappe.get_doc("AI Data Policy", "Individual Profile")
	spec = SEED["Individual Profile"]
	wanted = {
		**{f: ("Hidden", r) for f, r in spec["hidden"].items()},
		**{f: ("Read Only", r) for f, r in spec["read_only"].items()},
	}
	meta = frappe.get_meta("Individual Profile")
	policy.field_rules = [r for r in policy.field_rules if meta.has_field(r.policy_field) and r.policy_field not in wanted]
	for field, (handling, reason) in wanted.items():
		policy.append("field_rules", {"policy_field": field, "handling": handling, "reason": reason})
	policy.save(ignore_permissions=True)
	frappe.db.commit()
