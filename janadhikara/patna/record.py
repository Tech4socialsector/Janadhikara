"""The rules every Patna record form follows - the same ones as the Hyderabad and Guwahati profiles: a hidden
question keeps no answer, a question shown as mandatory is answered, only a Status the user's role may use is set,
the signed-in worker and their partner organisation are filled in, and a partner works only on its own records."""

import frappe
from frappe.model.document import Document

from janadhikara.security import enforce_own_partner
from janadhikara.validation import clear_hidden_answers, require_shown_answers


class PatnaRecord(Document):
	def validate(self):
		clear_hidden_answers(self)
		require_shown_answers(self)
		self.validate_validation_status()
		self.capture_from_logged_in_user()
		enforce_own_partner(self)

	def validate_validation_status(self):
		"""The Status question (the profiles): only an option the user's role may use can be set, and a Validated
		record is changed only by someone who may use Validated."""
		if not self.meta.has_field("validation_status"):
			return
		from janadhikara.masters.doctype.validation_status.validation_status import check_status_change

		check_status_change(self)

	def capture_from_logged_in_user(self):
		"""Backstop for records not created through the form: the signed-in user is the worker, their employee
		record the partner. Only fills what is empty (a form tied to a household or beneficiary takes its partner from it)."""
		from janadhikara.api import get_user_employee

		if not self.get("assigned_worker") and frappe.session.user != "Guest":
			self.assigned_worker = frappe.session.user
		if not self.get("partner_organization"):
			employee = get_user_employee()
			if employee:
				self.partner_organization = employee.parent
		if self.get("partner_organization") and not self.get("organization_name"):
			self.organization_name = frappe.db.get_value("Partner Details", self.partner_organization, "organization_name")
