# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.api import get_user_employee


class HouseholdProfile(Document):
	def validate(self):
		self.capture_from_logged_in_user()
		self.capture_surveyor()

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

	def capture_surveyor(self):
		# The surveyor is whoever is logged in when the household is first saved. Only filled when empty, so later edits by a
		# supervisor never overwrite who actually did the survey.
		user = frappe.session.user
		if not self.surveyor:
			self.surveyor = user
