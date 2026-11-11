# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

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
		self.validate_validation_status()

	def validate_validation_status(self):
		"""The Status question, with the same rule as on the Household and Individual Profile: only an option the user's
		role may use can be set, and a Validated record is changed only by someone who may use Validated."""
		from janadhikara.masters.doctype.validation_status.validation_status import check_status_change

		check_status_change(self)

	def validate_questionnaire(self):
		self.validate_location_hierarchy()

		# 2.2: the total population is Male + Female + Others
		parts = ("s2_population_male", "s2_population_female", "s2_population_others")
		if any(self.get(f) not in (None, "") for f in parts):
			self.s2_total_population = sum(cint(self.get(f)) for f in parts)

		# values can arrive as text from the form: compare them as numbers
		def more_than(part, whole, message):
			if self.get(part) not in (None, "") and self.get(whole) not in (None, "") and cint(self.get(part)) > cint(self.get(whole)):
				frappe.throw(message)

		more_than("s2_migrant_household_count", "s2_total_households", _("2.12: Migrant households can't be more than the total number of households (2.1)."))
		more_than("s3_households_affected", "s2_total_households", _("3.14: Households affected by eviction can't be more than the total number of households (2.1)."))
		more_than("s2_elderly_living_alone", "s2_elderly_60_plus", _("2.9: Elderly persons living alone can't be more than the elderly persons (2.8)."))

	def validate_location_hierarchy(self):
		"""1.1 to 1.4: the zone, circle and ward must belong to the corporation, zone and circle chosen above them."""
		levels = (
			("s1_zone", "Municipal Zone", "municipal_corporation", "s1_municipal_corporation", _("Zone")),
			("s1_circle", "Municipal Circle", "zone", "s1_zone", _("Circle")),
			("s1_ward", "Municipal Ward", "circle", "s1_circle", _("Ward")),
		)
		for field, doctype, parent_field, parent, label in levels:
			if self.get(field) and self.get(parent):
				if frappe.db.get_value(doctype, self.get(field), parent_field) != self.get(parent):
					frappe.throw(_("{0} {1} does not belong to {2}.").format(label, frappe.bold(self.get(field)), frappe.bold(self.get(parent))))

	def fill_partner(self):
		"""The partner organisation of the signed-in worker, when none was chosen (and its name, for lists and exports)."""
		if not self.partner_organization:
			from janadhikara.api import get_user_employee

			employee = get_user_employee()
			if employee:
				self.partner_organization = employee.parent
		if self.partner_organization and not self.organization_name:
			self.organization_name = frappe.db.get_value("Partner Details", self.partner_organization, "organization_name")

	def fill_orw_name(self):
		"""Name of the ORW (a User): the signed-in user, when left empty."""
		if not self.orw_name and frappe.session.user != "Guest":
			self.orw_name = frappe.session.user

