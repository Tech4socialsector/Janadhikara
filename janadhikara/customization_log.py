"""Keeps a log of what is changed in Customize Form (Property Setters) and in Custom Fields on this app's doctypes,
so the changes made on a cloud site can be carried over to the code. Each line is a Customization Log record."""
import json

import frappe

APP_MODULES = ("Masters", "App Config", "Engine", "Baseline")
LOG = "Customization Log"
SKIP_PROPERTIES = {"modified", "modified_by", "creation", "owner", "idx", "docstatus", "name", "parent", "parentfield", "parenttype", "doctype"}
CUSTOM_FIELD_KEYS = ("label", "fieldtype", "options", "reqd", "hidden", "read_only", "default", "description", "insert_after", "depends_on", "mandatory_depends_on", "in_list_view", "in_standard_filter", "fetch_from")


def _tracked(doctype):
	if not doctype or doctype == LOG or frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return False
	return frappe.db.get_value("DocType", doctype, "module") in APP_MODULES


def _original(doc):
	"""The value the app's own definition has for a Property Setter's setting."""
	try:
		if doc.doctype_or_field == "DocField":
			return frappe.db.get_value("DocField", {"parent": doc.doc_type, "fieldname": doc.field_name}, doc.property)
		return frappe.db.get_value("DocType", doc.doc_type, doc.property)
	except Exception:
		return None


def _write(**values):
	try:
		frappe.get_doc({"doctype": LOG, "changed_by": frappe.session.user, **values}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Customization Log not written", message=frappe.get_traceback())


def _recent_removal(doc):
	"""Customize Form saves a changed setting by deleting its Property Setter and creating a new one. When this setting was
	removed a moment ago by the same user, the change is one "Changed" line (from the removed value), not two."""
	rows = frappe.get_all(
		LOG,
		filters={
			"action": "Removed", "target_doctype": doc.doc_type, "fieldname": doc.field_name or "", "property": doc.property,
			"changed_by": frappe.session.user, "creation": [">", frappe.utils.add_to_date(None, seconds=-60)],
		},
		fields=["name", "previous_value"],
		order_by="creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def property_setter_created(doc, method=None):
	if not _tracked(doc.doc_type):
		return
	removed = _recent_removal(doc)
	if removed:
		frappe.db.set_value(
			LOG, removed.name,
			{"action": "Changed", "new_value": _str(doc.value), "changed_on": frappe.utils.now_datetime()},
			update_modified=False,
		)
		return
	_write(
		action="Created", target_doctype=doc.doc_type, fieldname=doc.field_name, property=doc.property,
		previous_value=_str(_original(doc)), new_value=_str(doc.value),
		details=json.dumps({"property_setter": doc.name, "type": doc.property_type, "level": doc.doctype_or_field}),
	)


def property_setter_changed(doc, method=None):
	if doc.flags.in_insert or not _tracked(doc.doc_type):
		return
	before = doc.get_doc_before_save()
	if before is not None and _str(before.value) == _str(doc.value):
		return
	_write(
		action="Changed", target_doctype=doc.doc_type, fieldname=doc.field_name, property=doc.property,
		previous_value=_str(before.value if before else _original(doc)), new_value=_str(doc.value),
		details=json.dumps({"property_setter": doc.name, "type": doc.property_type, "level": doc.doctype_or_field}),
	)


def property_setter_removed(doc, method=None):
	if not _tracked(doc.doc_type):
		return
	_write(
		action="Removed", target_doctype=doc.doc_type, fieldname=doc.field_name, property=doc.property,
		previous_value=_str(doc.value), new_value=_str(_original(doc)),
		details=json.dumps({"property_setter": doc.name, "note": "customization removed: back to the app's value"}),
	)


def custom_field_created(doc, method=None):
	if not _tracked(doc.dt):
		return
	_write(
		action="Created", target_doctype=doc.dt, fieldname=doc.fieldname, property="custom field",
		new_value=_str(doc.label or doc.fieldname),
		details=json.dumps({k: doc.get(k) for k in CUSTOM_FIELD_KEYS if doc.get(k) not in (None, "", 0)}, default=str),
	)


def custom_field_changed(doc, method=None):
	if doc.flags.in_insert or not _tracked(doc.dt):
		return
	before = doc.get_doc_before_save()
	if before is None:
		return
	for key in CUSTOM_FIELD_KEYS:
		if _str(before.get(key)) != _str(doc.get(key)):
			_write(
				action="Changed", target_doctype=doc.dt, fieldname=doc.fieldname, property=key,
				previous_value=_str(before.get(key)), new_value=_str(doc.get(key)),
				details=json.dumps({"custom_field": doc.name}),
			)


def custom_field_deleted(doc, method=None):
	if not _tracked(doc.dt):
		return
	_write(
		action="Deleted", target_doctype=doc.dt, fieldname=doc.fieldname, property="custom field",
		previous_value=_str(doc.label or doc.fieldname),
		details=json.dumps({k: doc.get(k) for k in CUSTOM_FIELD_KEYS if doc.get(k) not in (None, "", 0)}, default=str),
	)


def _str(value):
	return "" if value is None else str(value)
