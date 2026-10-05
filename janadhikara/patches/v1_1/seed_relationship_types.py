import frappe

RELATIONSHIPS = [
	"Self",
	"Spouse",
	"Father",
	"Mother",
	"Son",
	"Daughter",
	"Brother",
	"Sister",
	"Grandfather",
	"Grandmother",
	"Grandson",
	"Granddaughter",
	"Father-in-law",
	"Mother-in-law",
	"Son-in-law",
	"Daughter-in-law",
	"Brother-in-law",
	"Sister-in-law",
	"Uncle",
	"Aunt",
	"Nephew",
	"Niece",
	"Cousin",
	"Other Relative",
	"Not Related",
]


def execute():
	"""Starter list for Relationship Type (how a person relates to the head of the
	household). Only adds what is missing, so edits and extra entries survive."""
	for name in RELATIONSHIPS:
		if not frappe.db.exists("Relationship Type", name):
			frappe.get_doc({"doctype": "Relationship Type", "relationship_name": name}).insert(
				ignore_permissions=True
			)
	frappe.db.commit()
