import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""ToDo gets a "Due Time" next to its Due Date (the Worklist shows both)."""
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "task_time",
					"fieldtype": "Time",
					"label": "Due Time",
					"insert_after": "date",
					"description": "Optional - the time of day the task is due.",
				}
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="ToDo")
