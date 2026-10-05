# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from janadhikara.naming import autoname_with_code


class SettlementInterventionUnit(Document):
	def autoname(self):
		autoname_with_code(self, "SIU", "intervention_unit_code")
