# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

CHOICE_TYPES = ("Select", "Multi-select")


class QuestionBank(Document):
	def validate(self):
		self.question_no = (self.question_no or "").strip()
		self.validate_for_doctype()
		self.validate_grouping()
		self.validate_options()
		self.validate_condition()
		self.validate_display_conditions()

	def validate_for_doctype(self):
		from janadhikara.questions import ensure_answers_table

		ensure_answers_table(self.for_doctype)

	def validate_grouping(self):
		"""Individual question / Section / Tab: keep only the grouping the chosen type uses."""
		kind = self.group_type or "Individual question"
		self.group_type = kind
		self.section_group = (self.section_group or "").strip() or None
		self.tab_group = (self.tab_group or "").strip() or None
		if kind == "Individual question":
			self.section_group = self.tab_group = None
		elif kind == "Section":
			self.tab_group = None
			if not self.section_group:
				frappe.throw(_("Enter the section name."))
		elif not self.tab_group:
			frappe.throw(_("Enter the tab name."))

	def validate_options(self):
		if self.answer_type in CHOICE_TYPES:
			options = [o.strip() for o in (self.options or "").splitlines() if o.strip()]
			if len(options) < 2:
				frappe.throw(_("Give at least two options (one per line) for a {0} question.").format(self.answer_type))
			if len(set(options)) != len(options):
				frappe.throw(_("Options must be different from each other."))
			self.options = "\n".join(options)
		else:
			self.options = None

	def validate_condition(self):
		if bool(self.depends_on_question) != bool((self.depends_on_answer or "").strip()):
			frappe.throw(_("Set both the other question and the answer it must have - or neither."))
		if self.depends_on_question and self.depends_on_question == self.name:
			frappe.throw(_("A question cannot depend on itself."))

	def validate_display_conditions(self):
		"""'Display depends on': a field of a doctype, a condition and (for = / !=) a value."""
		for prefix, label in (("show_if", _("Display depends on")), ("section_show_if", _("Section display depends on"))):
			doctype = self.get(f"{prefix}_doctype")
			if not doctype:
				for key in ("field", "value"):
					self.set(f"{prefix}_{key}", None)
				continue
			fieldname = (self.get(f"{prefix}_field") or "").strip()
			if not fieldname or not frappe.get_meta(doctype).has_field(fieldname):
				frappe.throw(_("{0}: {1} has no field {2}.").format(label, frappe.bold(doctype), frappe.bold(fieldname or "-")))
			operator = self.get(f"{prefix}_operator") or "="
			value = (self.get(f"{prefix}_value") or "").strip()
			if operator in ("=", "!=") and not value:
				frappe.throw(_("{0}: enter the value to compare with.").format(label))
			self.set(f"{prefix}_field", fieldname)
			self.set(f"{prefix}_operator", operator)
			self.set(f"{prefix}_value", value if operator in ("=", "!=") else None)

	def on_update(self):
		"""Everyone in a section follows the section's own display condition."""
		if not self.section_group:
			return
		values = {
			key: self.get(f"section_show_if_{key}") for key in ("doctype", "field", "operator", "value")
		}
		frappe.db.set_value(
			"Question Bank",
			{"section_group": self.section_group, "name": ["!=", self.name]},
			{f"section_show_if_{key}": value for key, value in values.items()},
			update_modified=False,
		)
