import frappe


def execute():
	"""The Household Profile's validation hint now says Cluster Coordinator: drop the old translations (the new ones are imported on migrate)."""
	frappe.db.delete(
		"Translation",
		{"context": "janadhikara:field:Household Profile:validation_status:description", "source_text": "Area Coordinator to validate"},
	)
