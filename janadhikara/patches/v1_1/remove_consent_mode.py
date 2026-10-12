import frappe


def execute():
	"""Consent Mode is gone: drop its translations."""
	frappe.db.delete("Translation", {"context": ["like", "%consent_mode%"]})
	frappe.db.delete("Translation", {"context": ["like", "janadhikara:%"], "source_text": "Consent Mode"})
	frappe.db.delete(
		"Translation", {"context": "janadhikara:option", "source_text": ["in", ["Written", "Verbal (recorded)", "Digital"]]}
	)
