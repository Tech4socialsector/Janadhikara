"""The ToDo changes the app relies on (Task Title, Due Time, and the shorter ToDo form).

They used to be made only by one-off patches, which a fresh install skips - and the Worklist then failed with "Field not
permitted in query: task_title". This is the same setup as an idempotent function, run on install and on every migrate."""
import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

HIDDEN_FIELDS = ("color", "role", "sender", "assignment_rule")


def _setting_exists(doctype, property_, field_name=None):
	filters = {"doc_type": doctype, "property": property_}
	if field_name:
		filters["field_name"] = field_name
	return bool(frappe.db.exists("Property Setter", filters))


def ensure_todo_setup():
	if not frappe.db.exists("DocType", "ToDo"):
		return
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "task_title",
					"fieldtype": "Data",
					"label": "Task Title",
					"insert_after": "description_and_status",
					"in_list_view": 1,
					"bold": 1,
					"length": 140,
					"description": "A short name for the task. The description below holds the details.",
				},
				{
					"fieldname": "task_time",
					"fieldtype": "Time",
					"label": "Due Time",
					"insert_after": "date",
					"description": "Optional - the time of day the task is due.",
				},
			]
		},
		update=False,
	)
	frappe.clear_cache(doctype="ToDo")

	# Title first, then the rest (only when nobody has arranged the form yet).
	if not _setting_exists("ToDo", "field_order"):
		meta = frappe.get_meta("ToDo")
		others = [f for f in (meta.get("field_order") or [df.fieldname for df in meta.fields]) if f != "task_title"]
		frappe.make_property_setter(
			{"doctype": "ToDo", "doctype_or_field": "DocType", "property": "field_order", "value": json.dumps(["task_title"] + others), "property_type": "Data"},
			ignore_validate=True,
		)
	if not _setting_exists("ToDo", "title_field"):
		frappe.make_property_setter(
			{"doctype": "ToDo", "doctype_or_field": "DocType", "property": "title_field", "value": "task_title", "property_type": "Data"},
			ignore_validate=True,
		)
	for fieldname in HIDDEN_FIELDS:
		if not _setting_exists("ToDo", "hidden", fieldname):
			frappe.make_property_setter(
				{"doctype": "ToDo", "doctype_or_field": "DocField", "fieldname": fieldname, "property": "hidden", "value": "1", "property_type": "Check"},
				ignore_validate=True,
			)
	frappe.clear_cache(doctype="ToDo")
	frappe.db.commit()
