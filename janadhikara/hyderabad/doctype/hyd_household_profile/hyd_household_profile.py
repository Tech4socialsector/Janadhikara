# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.api import get_user_employee
from janadhikara.naming import autoname_with_code
from janadhikara.security import enforce_own_partner
from janadhikara.validation import clear_hidden_answers, require_shown_answers

SETTLEMENT = "HYD Settlement Profile"


class HYDHouseholdProfile(Document):
	"""The Hyderabad Urban Program's household profile (HH level profiling). It follows the same rules as the
	shared Household Profile - partner isolation, the Status workflow, the worklist - on Hyderabad's own questions."""

	def autoname(self):
		autoname_with_code(self, "HYD-HH", "hhid")

	def validate(self):
		clear_hidden_answers(self)
		require_shown_answers(self)
		self.set_member_count()
		self.set_household_label()
		self.validate_validation_status()
		self.fill_from_places()
		self.capture_from_logged_in_user()
		enforce_own_partner(self)

	def on_update(self):
		count_households(self.settlement)
		if self.has_value_changed("settlement"):
			count_households((self.get_doc_before_save() or frappe._dict()).get("settlement"))

	def after_delete(self):
		count_households(self.settlement)

	def set_member_count(self):
		"""The members of the family: the rows of the household roster. It decides how many Individual profiles are
		expected, and the 'profiles equal members' box follows the profiles captured."""
		self.member_count = len(self.household_roster or [])
		if not self.is_new():
			self.profiles_match_members = int(
				bool(self.member_count) and frappe.db.count("HYD Individual Profile", {"household": self.name}) == self.member_count
			)

	def set_household_label(self):
		self.household_label = household_label(self)

	def validate_validation_status(self):
		"""The Status question: only an option the user's role may use can be set, and a Validated record is
		changed only by someone who may use Validated."""
		from janadhikara.masters.doctype.validation_status.validation_status import check_status_change

		check_status_change(self)

	def fill_from_places(self):
		"""The partner follows the settlement."""
		if self.settlement and not self.partner_organization:
			self.partner_organization = frappe.db.get_value(SETTLEMENT, self.settlement, "partner_organization")

	def capture_from_logged_in_user(self):
		"""Backstop for records not created through the form: the signed-in user is the staff member, their
		employee record the partner. Only fills what is empty."""
		if not self.assigned_worker and frappe.session.user != "Guest":
			self.assigned_worker = frappe.session.user
		employee = get_user_employee()
		if employee and not self.partner_organization:
			self.partner_organization = employee.parent
		if self.partner_organization and not self.organization_name:
			self.organization_name = frappe.db.get_value("Partner Details", self.partner_organization, "organization_name")


def refresh_profiles_match(household):
	"""Tick (or untick) a household's 'Individual profiles equal the members' box after a profile is added, changed or removed."""
	if not household or not frappe.db.exists("HYD Household Profile", household):
		return
	members = frappe.db.count("HYD Household Member", {"parent": household, "parenttype": "HYD Household Profile"})
	profiles = frappe.db.count("HYD Individual Profile", {"household": household})
	frappe.db.set_value("HYD Household Profile", household, "profiles_match_members", int(bool(members) and profiles == members), update_modified=False)


def sync_roster(profile, household=None, remove=False):
	"""Keep a household's roster in step with its Individual Profiles: a profile has one roster row (made when the profile
	is saved, updated when it changes, removed when it is deleted or moved to another household)."""
	household = household or profile.household
	if not household or not frappe.db.exists("HYD Household Profile", household):
		return
	parent = frappe.get_doc("HYD Household Profile", household)
	row = next((r for r in parent.household_roster if r.individual_profile == profile.name), None)
	if remove:
		if not row:
			return
		parent.remove(row)
	else:
		if not row:
			# a member already named on the roster (no profile yet) is this profile's row; otherwise it is a new member
			name = (profile.member_name or "").strip().lower()
			row = next((r for r in parent.household_roster if not r.individual_profile and (r.member_name or "").strip().lower() == name), None)
			if row:
				row.individual_profile = profile.name
			else:
				row = parent.append("household_roster", {"individual_profile": profile.name})
		row.member_name = profile.member_name
		row.uin = profile.individual_id  # the roster's ID follows the profile (it is read-only there)
		row.date_of_birth = profile.date_of_birth or row.date_of_birth
		row.age = profile.age if profile.age is not None else row.age
		row.gender = profile.sex or row.gender
	parent.flags.ignore_permissions = True
	parent.save()


def count_households(settlement):
	"""The number of households captured in a settlement, kept up to date automatically."""
	if settlement and frappe.db.exists(SETTLEMENT, settlement):
		frappe.db.set_value(
			SETTLEMENT, settlement, "households_profiled", frappe.db.count("HYD Household Profile", {"settlement": settlement}), update_modified=False
		)


def household_label(doc):
	"""How a household is shown when picked (its ID, respondent and house), so households of the same name can be told apart."""
	house = _("House {0}").format(doc.get("house_no")) if doc.get("house_no") else None
	return " · ".join(v for v in (doc.get("hhid") or doc.name, doc.get("respondent_name"), house) if v)
