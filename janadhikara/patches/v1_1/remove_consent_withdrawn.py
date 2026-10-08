import frappe

OLD_NOTICE = "Withdrawal: they can withdraw consent at any time, as easily as it was given. After that, the record can no longer be changed and the data is erased once the purpose is over."


def execute():
	"""Consent Withdrawn On is gone (and with it the "record is frozen" rule): drop its translations and the old notice wording."""
	frappe.db.delete("Translation", {"context": ["like", "%consent_withdrawn_on%"]})
	frappe.db.delete("Translation", {"context": ["like", "janadhikara:%"], "source_text": "Consent Withdrawn On"})
	frappe.db.delete("Translation", {"context": "janadhikara:dpdp", "source_text": OLD_NOTICE})
