import frappe


def execute():
	"""Individual sheet changes: the EWS question moved under the Income Certificate (now 45.1) and Q52 was removed. Drop
	the translations of the old wording (the new ones are imported on migrate)."""
	prefix = "janadhikara:field:Individual Profile:"
	frappe.db.delete("Translation", {"context": prefix + "doc_ews:label", "source_text": "51. Do you have an EWS Certificate?"})
	frappe.db.delete("Translation", {"context": ["like", prefix + "disability_in_family:%"]})
