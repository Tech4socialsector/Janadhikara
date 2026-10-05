import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from janadhikara.worklist import ensure_task_title


def execute():
	"""ToDo gets a "Task Title" (short, shown first) ahead of the description.
	Existing tasks get a title cut from their description."""
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
				}
			]
		},
		update=True,
	)

	# Title first, then status / priority..., then the description (as in the app).
	meta = frappe.get_meta("ToDo")
	others = [f for f in (meta.get("field_order") or [df.fieldname for df in meta.fields]) if f != "task_title"]
	frappe.make_property_setter(
		{
			"doctype": "ToDo",
			"doctype_or_field": "DocType",
			"property": "field_order",
			"value": json.dumps(["task_title"] + others),
			"property_type": "Data",
		},
		ignore_validate=True,
	)
	frappe.make_property_setter(
		{"doctype": "ToDo", "doctype_or_field": "DocType", "property": "title_field", "value": "task_title", "property_type": "Data"},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="ToDo")

	for name in frappe.get_all("ToDo", filters={"task_title": ["in", ["", None]]}, pluck="name"):
		doc = frappe.get_doc("ToDo", name)
		ensure_task_title(doc)
		frappe.db.set_value("ToDo", name, "task_title", doc.task_title, update_modified=False)
	frappe.db.commit()
