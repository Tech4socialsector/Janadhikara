# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, today

from janadhikara.api import get_user_employee
from janadhikara.naming import autoname_with_code
from janadhikara.security import enforce_own_partner
from janadhikara.validation import clear_hidden_answers, require_shown_answers


class HouseholdProfile(Document):
	def autoname(self):
		autoname_with_code(self, "HH", "hhid")

	def before_insert(self):
		# House ID: generated, never typed
		if not self.house_id:
			self.house_id = make_autoname("HOU.####", self.doctype)

	def validate(self):
		clear_hidden_answers(self)
		require_shown_answers(self)
		self.validate_consent()
		self.head_from_respondent()
		self.validate_validation_status()
		self.validate_allotted_state()
		self.fill_from_places()
		self.set_profiles_match()
		self.capture_from_logged_in_user()
		enforce_own_partner(self)

	def validate_consent(self):
		"""DPDP: the respondent's details are only collected once consent is recorded."""
		if self.availability_for_survey != "Going Ahead":
			return
		if not self.consent_given:
			frappe.throw(_("Record the respondent's consent (DPDP) before collecting the household's details."))
		self.consent_date = self.consent_date or today()
		self.consent_taken_by = self.consent_taken_by or frappe.session.user

	def head_from_respondent(self):
		"""When nobody was named as the head, the respondent is the head of the family."""
		if not self.household_head_name and self.respondent_name:
			self.household_head_name = self.respondent_name

	def validate_allotted_state(self):
		if self.allotted_state and self.allotted_state.strip().lower() == "assam":
			frappe.throw(_("Q32 is for a house outside Assam: choose a state other than Assam, or pick the district of Assam in Q31."))

	def fill_from_places(self):
		"""The partner follows the settlement."""
		if self.settlement and not self.partner_organization:
			self.partner_organization = frappe.db.get_value("Settlement", self.settlement, "partner_organization")

	def set_profiles_match(self):
		"""Ticked when the Individual Profiles captured equal the members staying in the household."""
		if self.is_new():
			return
		self.profiles_match_members = int(
			self.member_count not in (None, "") and frappe.db.count("Individual Profile", {"household": self.name}) == cint(self.member_count)
		)

	def validate_validation_status(self):
		"""The Status question: only an option the user's role may use can be set, and a Validated record is
		changed only by someone who may use Validated (the dropdown already hides the rest; this stops a
		hand-made request)."""
		from janadhikara.masters.doctype.validation_status.validation_status import check_status_change

		check_status_change(self)

	def capture_from_logged_in_user(self):
		"""Backstop for records not created through the form (imports, API):
		the signed-in user fills the ORW name (Name of the ORW) and their employee
		record the partner. Only fills what's empty."""
		if not self.assigned_worker and frappe.session.user != "Guest":
			self.assigned_worker = frappe.session.user
		employee = get_user_employee()
		if employee and not self.partner_organization:
			self.partner_organization = employee.parent
		if self.partner_organization and not self.organization_name:
			self.organization_name = frappe.db.get_value("Partner Details", self.partner_organization, "organization_name")
