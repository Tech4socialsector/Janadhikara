import frappe

# Hyderabad: the app keeps only the Settlement profile, and is offered in English only.
REMOVED_DOCTYPES = (
	# forms first, then the tables and masters only they used
	"Household Profile",
	"Individual Profile",
	"Education Record",
	"Entitlement",
	"Health Condition",
	"Individual Document",
	"Household Cooking Fuel",
	"Cooking Fuel",
	"Relationship Type",
	"Welfare Board",
	"Assam District",
)
REMOVED_LANGUAGES = ("as", "hi")


def execute():
	for doctype in REMOVED_DOCTYPES:
		for dt, field in (
			("App Module DocType Item", "doctype_name"),
			("Field Function Mapping", "target_doctype"),
			("AI Data Policy", "name"),
			("Property Setter", "doc_type"),
			("Custom Field", "dt"),
			("ToDo", "reference_type"),
		):
			if frappe.db.table_exists(dt) and frappe.db.has_column(dt, field):
				frappe.db.delete(dt, {field: doctype})
		for question in frappe.get_all("Question Bank", filters={"for_doctype": doctype}, pluck="name"):
			frappe.delete_doc("Question Bank", question, force=True, ignore_permissions=True)
		frappe.db.delete("Translation", {"context": ["like", f"janadhikara:field:{doctype}:%"]})
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True, ignore_missing=True)
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{doctype}`")

	# English only: no other language is offered, and its translations go
	frappe.db.delete("Translation", {"language": ["in", REMOVED_LANGUAGES], "context": ["like", "janadhikara:%"]})
	frappe.db.set_value("Language", {"name": ["in", REMOVED_LANGUAGES]}, "enabled", 0)
	frappe.db.set_value("User", {"language": ["in", REMOVED_LANGUAGES]}, "language", "en", update_modified=False)
	if frappe.db.get_default("lang") in REMOVED_LANGUAGES:
		frappe.db.set_default("lang", "en")
	frappe.clear_cache()
