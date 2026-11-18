# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from janadhikara.api import get_user_employee
from janadhikara.hyderabad.doctype.hyd_household_profile.hyd_household_profile import refresh_profiles_match, sync_roster
from janadhikara.security import enforce_own_partner
from janadhikara.validation import clear_hidden_answers, require_shown_answers

HOUSEHOLD = "HYD Household Profile"


class HYDIndividualProfile(Document):
	"""The Hyderabad Urban Program's individual profile. It follows the same rules as the shared Individual Profile -
	partner isolation and the Status workflow - on Hyderabad's own questions."""

	def validate(self):
		self.set_age()
		clear_hidden_answers(self)
		require_shown_answers(self)
		self.validate_validation_status()
		self.fill_from_household()
		self.capture_from_logged_in_user()
		enforce_own_partner(self)

	def on_update(self):
		before = (self.get_doc_before_save() or frappe._dict()).get("household")
		if before and before != self.household:  # moved to another household: leaves the old roster
			sync_roster(self, household=before, remove=True)
		sync_roster(self)
		refresh_profiles_match(self.household)
		if before and before != self.household:
			refresh_profiles_match(before)

	def after_delete(self):
		sync_roster(self, remove=True)
		refresh_profiles_match(self.household)

	def set_age(self):
		"""Age (completed years) follows the date of birth."""
		if not self.date_of_birth:
			self.age = None
			return
		born = getdate(self.date_of_birth)
		if born > getdate(today()):
			frappe.throw(_("Date of birth can't be in the future."))
		self.age = relativedelta(getdate(today()), born).years

	def validate_validation_status(self):
		"""Only a Status the user's role may use can be set, and a Validated record is changed only by someone who may use it."""
		from janadhikara.masters.doctype.validation_status.validation_status import check_status_change

		check_status_change(self)

	def fill_from_household(self):
		"""The settlement and partner follow the household (also for records made outside the form)."""
		if not self.household:
			return
		settlement, partner = frappe.db.get_value(HOUSEHOLD, self.household, ["settlement", "partner_organization"]) or (None, None)
		self.settlement = self.settlement or settlement
		self.partner_organization = self.partner_organization or partner
		if self.partner_organization and not self.organization_name:
			self.organization_name = frappe.db.get_value("Partner Details", self.partner_organization, "organization_name")

	def capture_from_logged_in_user(self):
		if not self.assigned_worker and frappe.session.user != "Guest":
			self.assigned_worker = frappe.session.user
		employee = get_user_employee()
		if employee and not self.partner_organization:
			self.partner_organization = employee.parent
