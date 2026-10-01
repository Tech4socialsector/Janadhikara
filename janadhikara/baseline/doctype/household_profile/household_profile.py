# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.api import find_survey_field_units, get_user_employee


class HouseholdProfile(Document):
	def validate(self):
		self.capture_from_logged_in_user()
		self.validate_survey_field_unit()
		self.capture_surveyor()

	def capture_from_logged_in_user(self):
		"""Backstop for records not created through the form (imports, API):
		the logged-in user's own employee record fills the partner and
		assigned worker, and the survey field unit follows from the
		settlement / intervention unit they chose. Only fills what's empty."""
		employee = get_user_employee()
		if employee:
			if not self.assigned_worker:
				self.assigned_worker = employee.name
			if not self.partner_organization:
				self.partner_organization = employee.parent
		if self.settlement and not self.survey_field_unit:
			matches = find_survey_field_units(self.settlement, self.settlement_intervention_unit, self.survey)
			if len(matches) == 1:
				self.survey_field_unit = matches[0].name

	def validate_survey_field_unit(self):
		if not self.survey_field_unit:
			return
		unit = frappe.db.get_value(
			"Survey Field Unit", self.survey_field_unit, ["settlement", "settlement_intervention_unit"], as_dict=True
		)
		if unit.settlement and self.settlement and unit.settlement != self.settlement:
			frappe.throw(
				_("Survey Field Unit {0} belongs to settlement {1}, not {2}.").format(
					frappe.bold(self.survey_field_unit), frappe.bold(unit.settlement), frappe.bold(self.settlement)
				)
			)
		if (
			unit.settlement_intervention_unit
			and self.settlement_intervention_unit
			and unit.settlement_intervention_unit != self.settlement_intervention_unit
		):
			frappe.throw(
				_("Survey Field Unit {0} belongs to intervention unit {1}, not {2}.").format(
					frappe.bold(self.survey_field_unit),
					frappe.bold(unit.settlement_intervention_unit),
					frappe.bold(self.settlement_intervention_unit),
				)
			)

	def capture_surveyor(self):
		# The surveyor is whoever is logged in when the household (or a member
		# row) is first saved. Only filled when empty, so later edits by a
		# supervisor never overwrite who actually did the survey.
		user = frappe.session.user
		if not self.surveyor:
			self.surveyor = user
		for member in self.household_members or []:
			if not member.surveyor:
				member.surveyor = user
