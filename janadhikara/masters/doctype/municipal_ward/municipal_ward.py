# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MunicipalWard(Document):
	def validate(self):
		# a ward sits in one circle, which sits in one zone of one corporation
		if self.circle:
			self.zone = frappe.db.get_value("Municipal Circle", self.circle, "zone")
		if self.zone:
			self.municipal_corporation = frappe.db.get_value("Municipal Zone", self.zone, "municipal_corporation")
