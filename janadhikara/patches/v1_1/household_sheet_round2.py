import frappe

OLD_DISABILITY_NOTE = "The details about Pension and UDID will come under Individual Profile & Entitlements section.\nIf Yes, questions 105 to 106 are shown in the Individual Profile."


def execute():
	"""Household sheet changes: the language Rajbanshi is now spelled Rajbongshi (carry saved answers over), and the
	translations of the old wording are dropped (the new ones are imported on migrate)."""
	frappe.db.sql(
		"update `tabHousehold Profile` set languages_spoken = replace(languages_spoken, 'Rajbanshi', 'Rajbongshi') where languages_spoken like '%%Rajbanshi%%'"
	)
	prefix = "janadhikara:field:Household Profile:"
	frappe.db.delete("Translation", {"context": prefix + "languages_spoken:option", "source_text": "Rajbanshi"})
	frappe.db.delete("Translation", {"context": prefix + "person_with_disability:description", "source_text": OLD_DISABILITY_NOTE})
