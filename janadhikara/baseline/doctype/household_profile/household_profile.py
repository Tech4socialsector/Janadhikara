# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.naming import autoname_with_code

from janadhikara.api import get_user_employee
from janadhikara.questions import validate_answers


class HouseholdProfile(Document):
	def autoname(self):
		autoname_with_code(self, "HH", "hhid")

	def validate(self):
		self.validate_house_details()
		validate_answers(self)
		self.validate_validation_status()
		self.capture_from_logged_in_user()

	def validate_house_details(self):
		if self.stay_months is not None and not 0 <= self.stay_months <= 11:
			frappe.throw(_("Months staying here must be between 0 and 11."))
		if self.house_structure != "Multi-storied":
			self.floor_number = None  # only meaningful for a multi-storied house

	def validate_validation_status(self):
		"""Only a status the user's role may use can be set (the dropdown already hides the rest;
		this stops a hand-made request)."""
		from janadhikara.masters.doctype.validation_status.validation_status import is_usable_by

		if self.validation_status and (self.is_new() or self.has_value_changed("validation_status")):
			if not is_usable_by(self.validation_status):
				frappe.throw(
					_("You can't set the validation status {0}.").format(frappe.bold(self.validation_status)),
					frappe.PermissionError,
				)

	def capture_from_logged_in_user(self):
		"""Backstop for records not created through the form (imports, API):
		the logged-in user's own employee record fills the partner and
		assigned worker. Only fills what's empty."""
		employee = get_user_employee()
		if employee:
			if not self.assigned_worker:
				self.assigned_worker = employee.name
			if not self.partner_organization:
				self.partner_organization = employee.parent
