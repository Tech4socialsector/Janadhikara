# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from janadhikara.security import enforce_own_partner
from janadhikara.validation import clear_hidden_answers, require_shown_answers


class Settlement(Document):
	def validate(self):
		self.fill_partner()
		enforce_own_partner(self)
		self.fill_orw_name()
		clear_hidden_answers(self)
		require_shown_answers(self)
		self.validate_questionnaire()

	def validate_questionnaire(self):
		# values can arrive as text from the form: compare them as numbers
		# a "Yes" to a housing type means there is at least one such house
		for key in range(1, 10):
			answer = next((df.fieldname for df in self.meta.fields if df.fieldname.startswith(f"q6_{key}_") and df.fieldtype == "Select"), None)
			count = next((df.fieldname for df in self.meta.fields if df.fieldname.startswith(f"q6_{key}_1_")), None)
			if answer and count and self.get(answer) == "Yes" and self.get(count) not in (None, "") and flt(self.get(count)) < 1:
				frappe.throw(_("{0}: enter at least 1, or answer No above.").format(self.meta.get_label(count)))

		total = flt(self.get("q7_1_indicate_total_number_houses_physical"))
		families = self.get("q7_2_specify_total_number_families_currently")
		if families not in (None, "") and flt(families) < 0:
			frappe.throw(_("Number of families can't be negative."))

		shares = [flt(self.get(f"q16_1_{n}_proportion_children_going_{kind}")) for n, kind in ((2, "private_school"), (3, "government_sch"), (4, "government_aid"))]
		if sum(shares) > 100:
			frappe.throw(_("The shares of children going to private, government and government-aided schools add up to more than 100."))

		partial = flt(self.get("q20_3_if_yes_partially_no_houses"))
		if partial and total and partial > total:
			frappe.throw(_("Houses considered for the programme can't be more than the total number of houses in the settlement."))

	def fill_partner(self):
		"""The partner organisation of the signed-in worker, when none was chosen."""
		if self.partner_organization:
			return
		from janadhikara.api import get_user_employee

		employee = get_user_employee()
		if employee:
			self.partner_organization = employee.parent

	def fill_orw_name(self):
		"""Name of the ORW: whoever is creating the record, when left empty."""
		if self.orw_name:
			return
		from janadhikara.api import get_user_employee

		employee = get_user_employee()
		self.orw_name = (employee.worker_name if employee else None) or frappe.db.get_value(
			"User", frappe.session.user, "full_name"
		)

