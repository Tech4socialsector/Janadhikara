import frappe


def execute():
	"""The ToDo form in the app (opened from the Worklist and from notifications) shows
	only what matters: title, status, priority, due date and time, assignee,
	description and the linked record. Frappe's colour / role / sender / assignment
	rule fields are hidden."""
	for fieldname in ("color", "role", "sender", "assignment_rule"):
		frappe.make_property_setter(
			{
				"doctype": "ToDo",
				"doctype_or_field": "DocField",
				"fieldname": fieldname,
				"property": "hidden",
				"value": "1",
				"property_type": "Check",
			},
			ignore_validate=True,
		)
	frappe.clear_cache(doctype="ToDo")
