# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from janadhikara.guwahati.doctype.settlement.settlement import Settlement



class HYDSettlementProfile(Settlement):
	"""The Hyderabad Urban Program's settlement profile. It shares the partner, ORW and status rules of
	Settlement; the Guwahati questionnaire checks give way to Hyderabad's own."""

	def validate_questionnaire(self):
		for df in self.meta.fields:
			if df.fieldtype == "Percent" and self.get(df.fieldname) not in (None, "") and not 0 <= flt(self.get(df.fieldname)) <= 100:
				frappe.throw(_("{0} must be between 0 and 100.").format(_(df.label)))
		male, female, others = (flt(self.get(f"q2_{n}_total_population_{k}")) for n, k in ((2, "male"), (3, "female"), (4, "others")))
		if min(male, female, others) < 0:
			frappe.throw(_("Population counts can't be negative."))
