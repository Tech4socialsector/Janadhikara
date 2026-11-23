# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def item_roles(row):
	"""The roles typed in an item's Visible To Roles box (one per line, commas accepted too)."""
	return [r.strip() for line in (row.roles or "").splitlines() for r in line.split(",") if r.strip()]


class AppModuleGroup(Document):
	def validate(self):
		for row in self.items or []:
			for role in item_roles(row):
				if not frappe.db.exists("Role", role):
					frappe.throw(_("Row {0}: {1} is not a Role").format(row.idx, role))
