# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.ai.data_service import ALWAYS_BLOCKED, MAX_ROWS_HARD, POLICY_CACHE_KEY


class AIDataPolicy(Document):
	def validate(self):
		if self.enabled and self.target_doctype in ALWAYS_BLOCKED:
			frappe.throw(
				_("{0} can never be made available to the assistant - it holds access, configuration or the assistant's own guardrails.").format(
					frappe.bold(self.target_doctype)
				)
			)
		if self.can_write and not self.can_read:
			frappe.throw(_("The assistant can't edit records it isn't allowed to read - tick Can Read as well."))
		self.max_rows = min(max(frappe.utils.cint(self.max_rows) or 20, 1), MAX_ROWS_HARD)

		meta = frappe.get_meta(self.target_doctype)
		seen = set()
		for row in self.field_rules:
			if not meta.get_field(row.policy_field):
				frappe.throw(
					_("Row {0}: {1} isn't a field of {2}.").format(
						row.idx, frappe.bold(row.policy_field), frappe.bold(self.target_doctype)
					)
				)
			if row.policy_field in seen:
				frappe.throw(_("Row {0}: {1} is listed more than once.").format(row.idx, frappe.bold(row.policy_field)))
			seen.add(row.policy_field)

	def on_update(self):
		frappe.cache().delete_value(POLICY_CACHE_KEY)

	def on_trash(self):
		frappe.cache().delete_value(POLICY_CACHE_KEY)
