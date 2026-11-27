import frappe

# Patna keeps only Household Detail, Family Member, Entitlements, Mental Health Assessment, Medical OPD and
# Health Camp Record. These forms (and their records) are removed, with their Home menu items.
DROPPED = (
	"PTN Rescue",
	"PTN Shelter Home",
	"PTN Hygiene",
	"PTN Empowerment",
	"PTN Longterm Shelter",
	"PTN Beggars Home",
	"PTN Ambulance Request",
	"PTN Aftercare",
	"PTN Care Centre Admission",
	"PTN Medical IPD",
	"PTN Interventions",  # child table of Care Centre Admission only
)


def execute():
	if frappe.db.table_exists("App Module Group Item"):
		frappe.db.delete("App Module Group Item", {"item_type": "DocType", "doctype_name": ["in", DROPPED]})
	for doctype in DROPPED:
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True, ignore_missing=True)
		for dt, field in (("Property Setter", "doc_type"), ("Custom Field", "dt"), ("Client Script", "dt")):
			if frappe.db.table_exists(dt):
				frappe.db.delete(dt, {field: doctype})
	frappe.db.commit()
	frappe.clear_cache()
