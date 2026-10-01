# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AppModuleSetting(Document):
	def validate(self):
		self.validate_sidebar_items()

	def validate_sidebar_items(self):
		"""Sidebar items are Links, Section Breaks (group headings) and Spacers.
		A Link can be a child - shown indented - under the Link or the Section
		Break above it, so it needs something above it to hang from."""
		has_parent_above = False
		for row in self.doctypes or []:
			kind = row.item_type or "Link"
			if kind == "Link":
				if not row.doctype_name:
					frappe.throw(_("Row {0}: choose the DocType this item opens.").format(row.idx))
				if row.child and not has_parent_above:
					frappe.throw(
						_("Row {0}: a child item is shown indented under the Link or Section Break above it, but there's nothing above it yet.").format(
							row.idx
						)
					)
				has_parent_above = True
			elif kind == "Section Break":
				if not (row.label or "").strip():
					frappe.throw(_("Row {0}: a Section Break needs a label.").format(row.idx))
				if row.child:
					frappe.throw(_("Row {0}: only a Link can be a child item.").format(row.idx))
				has_parent_above = True
			else:  # Spacer - just a gap, keeps whatever is above it as the parent
				if row.child:
					frappe.throw(_("Row {0}: only a Link can be a child item.").format(row.idx))
