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
		self.set_household_label()
		self.set_member_count()
		self.validate_validation_status()
		self.fill_from_places()
		self.set_profiles_match()
		self.capture_from_logged_in_user()
		enforce_own_partner(self)

	def on_update(self):
		count_households(self.settlement)
		if self.has_value_changed("settlement"):
			count_households((self.get_doc_before_save() or frappe._dict()).get("settlement"))

	def after_delete(self):
		count_households(self.settlement)

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

	def set_member_count(self):
		"""Members of the family: the adults and children counted in 9.1 and 9.2 (no longer asked separately)."""
		if self.total_adults not in (None, "") or self.total_children not in (None, ""):
			self.member_count = cint(self.total_adults) + cint(self.total_children)

	def set_household_label(self):
		self.household_label = household_label(self)

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


def count_households(settlement):
	"""Settlement 7.3: the number of Household Profiles captured in the settlement, kept up to date automatically."""
	if settlement and frappe.db.exists("Settlement", settlement):
		frappe.db.set_value(
			"Settlement", settlement, "households_profiled", frappe.db.count("Household Profile", {"settlement": settlement}), update_modified=False
		)


def household_label(doc):
	"""How a household is shown when picking it (e.g. in an Individual Profile): the HHID, the head of the family and
	the house, so households whose heads share a name can be told apart."""
	house = ", ".join(v for v in (doc.get("house_no") and _("House {0}").format(doc.get("house_no")), doc.get("street_name")) if v)
	return " · ".join(v for v in (doc.get("hhid") or doc.get("name"), doc.get("household_head_name"), house) if v)
