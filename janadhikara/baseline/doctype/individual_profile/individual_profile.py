# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class IndividualProfile(Document):
	def validate(self):
		# The data collector is whoever is logged in when the person is first
		# saved - never overwritten by a later edit.
		if not self.surveyor:
			self.surveyor = frappe.session.user
		self.validate_consent()

	def validate_consent(self):
		"""DPDP: entitlement and document details are only collected with the
		person's consent, and not at all (or changed) once it is withdrawn."""
		if self.consent_given:
			if not self.consent_mode:
				frappe.throw(_("Consent Mode is required when consent is given."))
			if not self.consent_date:
				self.consent_date = today()
			if not self.consent_taken_by:
				self.consent_taken_by = frappe.session.user
		else:
			self.consent_withdrawn_on = None

		holds_data = bool(self.entitlements or self.documents)
		if holds_data and not self.consent_given:
			frappe.throw(
				_("Record the person's consent (Consent Given) before adding entitlement or document details.")
			)
		if holds_data and self.consent_withdrawn_on and self.has_value_changed_in_consent_tables():
			frappe.throw(
				_("Consent was withdrawn on {0}: entitlement and document details cannot be added or changed.").format(
					frappe.format(self.consent_withdrawn_on, {"fieldtype": "Date"})
				)
			)

	def has_value_changed_in_consent_tables(self):
		before = self.get_doc_before_save()
		if not before:
			return True
		for table in ("entitlements", "documents"):
			old_rows, new_rows = before.get(table), self.get(table)
			if [r.name for r in old_rows] != [r.name for r in new_rows]:
				return True
			for old_row, new_row in zip(old_rows, new_rows):
				for field in new_row.meta.fields:
					if field.fieldtype in ("Section Break", "Column Break"):
						continue
					if old_row.get(field.fieldname) != new_row.get(field.fieldname):
						return True
		return False
