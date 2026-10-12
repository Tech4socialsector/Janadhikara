"""The one "Status" question on a Household and an Individual Profile.

Its options are Validation Status records, and each record lists the roles that may use it (empty = everyone), so
the dropdown, the API and a hand-made request all agree. ORWs see Partially Completed and Completed;
coordinators also see Revision Needed and Validated. The roles can be changed in the Validation Status list."""
import frappe

COORDINATORS = ["Program Coordinator", "Program Manager", "Organization Admin"]
STATUSES = {
	"Partially Completed": [],
	"Completed": [],
	"Revision Needed": COORDINATORS,
	"Validated": COORDINATORS,
}


def ensure_statuses():
	"""Create the four options that are missing. A record that already exists (and any roles set on it) is left as it is."""
	for order, (name, roles) in enumerate(STATUSES.items(), start=1):
		if frappe.db.exists("Validation Status", name):
			if not frappe.db.get_value("Validation Status", name, "sequence"):
				frappe.db.set_value("Validation Status", name, "sequence", order, update_modified=False)
			continue
		frappe.get_doc(
			{
				"doctype": "Validation Status",
				"status_name": name,
				"enabled": 1,
				"sequence": order,
				"roles": [{"role": r} for r in roles if frappe.db.exists("Role", r)],
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
