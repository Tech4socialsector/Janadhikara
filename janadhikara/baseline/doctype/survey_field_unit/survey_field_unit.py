# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SurveyFieldUnit(Document):
	def validate(self):
		self.validate_unit_belongs_to_settlement()
		self.validate_not_duplicate()

	def validate_unit_belongs_to_settlement(self):
		if not self.settlement_intervention_unit:
			return
		if not self.settlement:
			frappe.throw(_("Choose the Settlement before choosing an Intervention Unit."))
		parent = frappe.db.get_value("Settlement Intervention Unit", self.settlement_intervention_unit, "parent")
		if parent != self.settlement:
			frappe.throw(
				_("{0} is not an intervention unit of {1}.").format(
					frappe.bold(self.settlement_intervention_unit), frappe.bold(self.settlement)
				)
			)

	def validate_not_duplicate(self):
		if not self.settlement:
			return
		existing = frappe.db.get_value(
			"Survey Field Unit",
			{
				"name": ["!=", self.name],
				"survey": self.survey or "",
				"settlement": self.settlement,
				"settlement_intervention_unit": self.settlement_intervention_unit or "",
				"status": "Active",
			},
			"name",
		)
		if existing and self.status == "Active":
			frappe.throw(
				_("{0} already covers this survey, settlement and intervention unit - there should be one active field unit per place.").format(
					frappe.bold(existing)
				)
			)
