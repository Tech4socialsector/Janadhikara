# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class OfflineSyncLog(Document):
	"""One line per record uploaded from a phone's offline queue. Its name is the phone's own id for the
	upload, so sending the same upload twice (the connection dropped before the reply arrived) finds this
	line and returns the earlier result instead of creating a duplicate. Written by janadhikara.offline only."""
