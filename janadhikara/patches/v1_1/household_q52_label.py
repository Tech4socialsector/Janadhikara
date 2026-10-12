import frappe


def execute():
	"""Question 52's wording changed: drop the translation record that still carries the old wording."""
	frappe.db.delete(
		"Translation",
		{
			"context": "janadhikara:field:Household Profile:knows_health_post:label",
			"source_text": "52. Do you know about nearest Urban Health Post/Health & Wellness Centre",
		},
	)
