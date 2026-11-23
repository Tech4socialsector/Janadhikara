# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SupportTicketReply(Document):
	"""One message in a ticket's conversation. Created through janadhikara.helpdesk.add_reply."""
