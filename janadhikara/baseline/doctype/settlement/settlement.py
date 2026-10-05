# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.naming import autoname_with_code


class Settlement(Document):
	def autoname(self):
		autoname_with_code(self, "SET", "settlement_code")

	def validate(self):
		self.validate_worker_assignments()

	def validate_worker_assignments(self):
		rows = self.worker_assignments or []
		if not rows:
			return
		if not self.partner_organization:
			frappe.throw(_("Choose the Partner Organization before tagging workers."))

		# A unit's own name is its code (see Settlement Intervention Unit's autoname).
		unit_codes = {u.intervention_unit_code for u in (self.intervention_units or [])}
		seen = set()
		for row in rows:
			worker_partner = frappe.db.get_value("Employee", row.worker, "parent")
			if worker_partner != self.partner_organization:
				frappe.throw(
					_("Row {0}: {1} is not a worker of {2}.").format(
						row.idx, frappe.bold(row.worker), frappe.bold(self.partner_organization)
					)
				)
			if row.intervention_unit:
				if not self.has_intervention_units:
					frappe.throw(
						_("Row {0}: this settlement has no intervention units - clear the unit or tick {1}.").format(
							row.idx, frappe.bold(_("Has Intervention Units"))
						)
					)
				if row.intervention_unit not in unit_codes:
					frappe.throw(
						_("Row {0}: {1} is not one of this settlement's intervention units.").format(
							row.idx, frappe.bold(row.intervention_unit)
						)
					)
			key = (row.worker, row.intervention_unit or "")
			if key in seen:
				frappe.throw(
					_("Row {0}: {1} is already tagged{2}.").format(
						row.idx,
						frappe.bold(row.worker),
						_(" to {0}").format(row.intervention_unit) if row.intervention_unit else "",
					)
				)
			seen.add(key)
