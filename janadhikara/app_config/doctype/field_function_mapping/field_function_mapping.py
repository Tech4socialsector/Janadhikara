# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.field_functions import FIELD_FUNCTIONS


class FieldFunctionMapping(Document):
	def validate(self):
		func = FIELD_FUNCTIONS.get(self.function_name)
		if not func:
			frappe.throw(_("Unknown function {0}.").format(frappe.bold(self.function_name)))

		meta = frappe.get_meta(self.target_doctype)
		self.validate_trigger_field(meta, func)
		self.validate_mappings(meta, func)

		self.function_description = func["description"]
		self.expression = self.build_expression(func)

	def validate_trigger_field(self, meta, func):
		df = meta.get_field(self.trigger_field)
		if not df:
			frappe.throw(
				_("Trigger Field {0} doesn't exist on {1}.").format(
					frappe.bold(self.trigger_field), frappe.bold(self.target_doctype)
				)
			)
		if df.fieldtype not in func["trigger_fieldtypes"]:
			frappe.throw(
				_("{0} can only be triggered by a {1} field, but {2} is {3}.").format(
					frappe.bold(self.function_name),
					", ".join(func["trigger_fieldtypes"]),
					frappe.bold(self.trigger_field),
					df.fieldtype,
				)
			)

	def validate_mappings(self, meta, func):
		seen_outputs, seen_targets = set(), set()
		needs_input = bool(func.get("input_fieldtypes"))
		input_fields = {row.input_field for row in self.field_mappings if row.input_field}
		if needs_input and len(input_fields) != 1:
			frappe.throw(
				_("{0} reads a second field: give every row the same {1}.").format(
					frappe.bold(self.function_name), frappe.bold(_("Also Uses Field"))
				)
			)
		if not needs_input and input_fields:
			frappe.throw(_("{0} doesn't use a second field - clear {1}.").format(frappe.bold(self.function_name), frappe.bold(_("Also Uses Field"))))
		for row in self.field_mappings:
			row.function_name = self.function_name
			if needs_input:
				idf = meta.get_field(row.input_field)
				if not idf:
					frappe.throw(_("Row {0}: {1} doesn't exist on {2}.").format(row.idx, frappe.bold(row.input_field), frappe.bold(self.target_doctype)))
				if idf.fieldtype not in func["input_fieldtypes"]:
					frappe.throw(
						_("Row {0}: {1} must be a {2} field, but {3} is {4}.").format(
							row.idx, frappe.bold(_("Also Uses Field")), ", ".join(func["input_fieldtypes"]), frappe.bold(row.input_field), idf.fieldtype
						)
					)
			output = func["outputs"].get(row.output)
			if not output:
				frappe.throw(
					_("Row {0}: {1} isn't an output of {2}. Valid outputs: {3}").format(
						row.idx, frappe.bold(row.output), self.function_name, ", ".join(func["outputs"])
					)
				)
			df = meta.get_field(row.target_field)
			if not df:
				frappe.throw(
					_("Row {0}: Target Field {1} doesn't exist on {2}.").format(
						row.idx, frappe.bold(row.target_field), frappe.bold(self.target_doctype)
					)
				)
			if df.fieldtype not in output["fieldtypes"]:
				frappe.throw(
					_("Row {0}: {1} ({2}) can only go into a {3} field, but {4} is {5}.").format(
						row.idx,
						output["label"],
						row.output,
						", ".join(output["fieldtypes"]),
						frappe.bold(row.target_field),
						df.fieldtype,
					)
				)
			if row.output in seen_outputs:
				frappe.throw(_("Row {0}: {1} is mapped more than once.").format(row.idx, row.output))
			if row.target_field in seen_targets:
				frappe.throw(_("Row {0}: {1} already receives another output.").format(row.idx, row.target_field))
			seen_outputs.add(row.output)
			seen_targets.add(row.target_field)

	def build_expression(self, func):
		lines = [f"{self.target_doctype}.{self.trigger_field} \u2192 {self.function_name}()"]
		for row in self.field_mappings:
			label = func["outputs"][row.output]["label"]
			suffix = "  (only if empty)" if row.only_if_empty else ""
			uses = f"  uses {row.input_field}" if row.input_field else ""
			lines.append(f"  {row.output} \u2192 {row.target_field}    [{label}]{uses}{suffix}")
		return "\n".join(lines)
