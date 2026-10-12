import frappe


def execute():
	"""Question 6 of the Individual Profile was reworded: drop the translation records that still carry the old wording."""
	frappe.db.delete("Translation", {"context": ["like", "janadhikara:field:Individual Profile:member_name:%"]})
