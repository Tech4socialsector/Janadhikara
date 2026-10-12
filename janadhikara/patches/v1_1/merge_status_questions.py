import frappe

from janadhikara.statuses import STATUSES, ensure_statuses


def execute():
	"""Documentation Status and Validation Status are one question now (Status). Make sure its four options exist, carry the
	old documentation status over where no validation status was set, and drop the translations of the changed questions
	(the new ones are imported on migrate)."""
	ensure_statuses()
	# Revision Needed and Validated are for coordinators: where nobody was ever listed, list them now
	for name, roles in STATUSES.items():
		if roles and not frappe.db.exists("Validation Status Role", {"parent": name, "parenttype": "Validation Status"}):
			doc = frappe.get_doc("Validation Status", name)
			for role in roles:
				if frappe.db.exists("Role", role):
					doc.append("roles", {"role": role})
			doc.save(ignore_permissions=True)
	for doctype, column in (("Household Profile", "status"), ("Individual Profile", "documentation_status")):
		if frappe.db.has_column(doctype, column):
			frappe.db.sql(
				f"""update `tab{doctype}` set validation_status = `{column}`
				where ifnull(validation_status, '') = '' and `{column}` in ('Completed', 'Partially Completed')"""
			)
	for doctype, fieldnames in (("Household Profile", ("status", "validation_status")), ("Individual Profile", ("documentation_status", "validation_status"))):
		for fieldname in fieldnames:
			frappe.db.delete("Translation", {"context": ["like", f"janadhikara:field:{doctype}:{fieldname}:%"]})
	frappe.db.commit()
