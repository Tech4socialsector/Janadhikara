import frappe

from janadhikara.ai.privacy import PERSONAL_FIELDNAMES

# Names, phone numbers, e-mail, addresses and positions are never sent to the external language model:
# every AI Data Policy gets a Hidden rule for each such field its doctype has.


def execute():
	for name in frappe.get_all("AI Data Policy", pluck="name"):
		doc = frappe.get_doc("AI Data Policy", name)
		if not frappe.db.exists("DocType", doc.target_doctype):
			continue
		fields = {df.fieldname for df in frappe.get_meta(doc.target_doctype).fields}
		kept = [row for row in doc.field_rules if row.policy_field in fields]  # rules of removed fields go
		changed = len(kept) != len(doc.field_rules)
		doc.field_rules = kept
		have = {row.policy_field: row for row in doc.field_rules}
		for field in sorted(PERSONAL_FIELDNAMES & fields):
			if field in have:
				if have[field].handling != "Hidden":
					have[field].handling = "Hidden"
					changed = True
			else:
				doc.append("field_rules", {"policy_field": field, "handling": "Hidden", "reason": "personal detail"})
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.cache().delete_value("janadhikara_ai_policies")
