# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class FormDraft(Document):
	"""A form someone is still filling in, kept on the server so a dropped session, a closed window or a lost phone does
	not lose it. Created and read only through janadhikara.drafts, for the signed-in user's own drafts."""
