import frappe


def execute():
	"""Household Member (now Individual Profile) used to be a child table of Household Profile. Now it is
	its own doctype with a `household` link: point every existing row at the
	household it was listed under, then give it the AI policy seed and a spot in
	the Baseline sidebar."""
	if frappe.db.has_column("Individual Profile", "parent"):
		frappe.db.sql(
			"""update `tabIndividual Profile` set household = parent
			where ifnull(household, '') = '' and ifnull(parent, '') != ''"""
		)

	from janadhikara.ai.policy import seed_policies

	seed_policies()

	# A policy seeded while it was a child table stays as-is; make sure the
	# confidential fields are hidden on the existing one too.
	if frappe.db.exists("AI Data Policy", "Individual Profile"):
		policy = frappe.get_doc("AI Data Policy", "Individual Profile")
		hidden = {r.policy_field for r in policy.field_rules}
		from janadhikara.ai.policy import SEED

		for field, reason in SEED["Individual Profile"]["hidden"].items():
			if field not in hidden:
				policy.append("field_rules", {"policy_field": field, "handling": "Hidden", "reason": reason})
		policy.save(ignore_permissions=True)

	setting = frappe.db.get_value("App Module Setting", {"module_name": "Baseline"}) or "Baseline"
	if frappe.db.exists("App Module Setting", setting):
		doc = frappe.get_doc("App Module Setting", setting)
		if not any(i.doctype_name == "Individual Profile" for i in doc.doctypes):
			doc.append("doctypes", {"item_type": "Link", "doctype_name": "Individual Profile", "label": "Individual Profile"})
			doc.save(ignore_permissions=True)
	frappe.db.commit()
