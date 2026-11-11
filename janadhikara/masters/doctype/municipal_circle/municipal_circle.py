# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MunicipalCircle(Document):
	def validate(self):
		if self.zone:
			self.municipal_corporation = frappe.db.get_value("Municipal Zone", self.zone, "municipal_corporation")
