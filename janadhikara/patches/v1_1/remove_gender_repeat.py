import frappe


def execute():
	"""The second Gender question (10) is gone: drop its translations (Q7 now carries its help text)."""
	frappe.db.delete("Translation", {"context": ["like", "janadhikara:field:Individual Profile:gender_repeat:%"]})
