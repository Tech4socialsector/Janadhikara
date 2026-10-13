# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CustomizationLog(Document):
	"""One line per change made in Customize Form (or to a Custom Field) on a site to one of this app's doctypes.
	Written by customization_log.py's hooks; only the follow-up (carried over to the code, notes) is edited by hand."""
