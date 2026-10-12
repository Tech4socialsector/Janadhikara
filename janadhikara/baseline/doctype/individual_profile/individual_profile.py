# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from janadhikara.naming import autoname_with_code
from janadhikara.security import enforce_own_partner
from janadhikara.validation import clear_hidden_answers, require_shown_answers


class IndividualProfile(Document):
	def autoname(self):
		autoname_with_code(self, "IND", "individual_id")

	def validate(self):
		self.validate_consent()
		self.fill_from_household()
		enforce_own_partner(self)
		self.age = age_in_years(self.date_of_birth)
		clear_hidden_answers(self)
		require_shown_answers(self)
		self.validate_occupation()
		self.validate_validation_status()

	def on_update(self):
		update_household_match(self.household)

	def on_trash(self):
		update_household_match(self.household, removing=self.name)

	def validate_consent(self):
		"""DPDP: nothing about a person is recorded without consent."""
		if not self.consent_given:
			frappe.throw(_("Record the person's consent (DPDP) before saving their details."))
		self.consent_date = self.consent_date or today()
		self.consent_taken_by = self.consent_taken_by or frappe.session.user

	def fill_from_household(self):
		"""Questions 2 to 5 come from the Household Profile, so they are never typed again."""
		if not self.household:
			return
		household = frappe.db.get_value(
			"Household Profile", self.household, ["hhid", "partner_organization", "settlement", "respondent_name", "pregnant_woman", "person_with_disability"], as_dict=True
		)
		if household:
			self.hhid = household.hhid
			self.implementing_org = household.partner_organization
			self.settlement_intervention_unit = household.settlement
			self.respondent_name = self.respondent_name or household.respondent_name
			self.household_has_pregnant = int(household.pregnant_woman == "Yes")
			self.household_has_disability = int(household.person_with_disability == "Yes")

	def validate_occupation(self):
		"""Up to 3 occupations; "Not working/Not applicable" stands alone."""
		chosen = [v.strip() for v in (self.occupation_1 or "").split("\n") if v.strip()]
		if len(chosen) > 3:
			frappe.throw(_("Select at most 3 occupations."))
		if "Not working/Not applicable" in chosen and len(chosen) > 1:
			frappe.throw(_("Not working/Not applicable can't be combined with another occupation."))

	def validate_validation_status(self):
		"""The Status question: only an option the user's role may use can be set, and a Validated record is
		changed only by someone who may use Validated."""
		from janadhikara.masters.doctype.validation_status.validation_status import check_status_change

		check_status_change(self)


def age_in_years(date_of_birth):
	"""Completed years since the date of birth (None when it isn't known)."""
	if not date_of_birth:
		return None
	born, now = getdate(date_of_birth), getdate(today())
	return max(0, now.year - born.year - ((now.month, now.day) < (born.month, born.day)))


def update_household_match(household, removing=None):
	"""Keep the household's "profiles captured equal the members" box in step with its profiles."""
	if not household or not frappe.db.exists("Household Profile", household):
		return
	members = frappe.db.get_value("Household Profile", household, "member_count")
	captured = frappe.db.count("Individual Profile", {"household": household}) - (1 if removing else 0)
	frappe.db.set_value(
		"Household Profile", household, "profiles_match_members", int(bool(members) and captured == members), update_modified=False
	)
