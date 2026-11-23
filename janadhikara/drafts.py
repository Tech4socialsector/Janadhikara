"""Drafts of unsaved forms, kept on the server for the person typing them.

A form is saved here every few seconds while it is being filled in (it can be incomplete: no mandatory-field checks),
so the work survives a closed window, a signed-out session or a different phone. A draft is private to its user, needs
the user's own permission to create / change the record it is for, is deleted when the record is saved and after
DRAFT_DAYS, and is never shown to the AI assistant (see ai/data_service.py ALWAYS_BLOCKED)."""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

DRAFT = "Form Draft"
DRAFT_DAYS = 7
MAX_BYTES = 2 * 1024 * 1024


def _key(doctype, name):
	return hashlib.sha1(f"{frappe.session.user}|{doctype}|{name or ''}".encode()).hexdigest()


def _check_access(doctype, name):
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to keep a draft."), frappe.PermissionError)
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("Unknown document type."))
	if name:
		if not frappe.has_permission(doctype, "write", name):
			frappe.throw(_("Not permitted."), frappe.PermissionError)
	elif not frappe.has_permission(doctype, "create"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def save_draft(doctype, name=None, data=None):
	"""Create or replace the signed-in user's draft of this form. `data` is the form's answers as JSON."""
	name = name or ""
	_check_access(doctype, name)
	if not isinstance(data, str):
		data = json.dumps(data)
	if len(data.encode()) > MAX_BYTES:
		frappe.throw(_("This draft is too large to keep."))
	try:
		parsed = json.loads(data)
	except ValueError:
		frappe.throw(_("The draft is not valid."))
	if not isinstance(parsed, dict):
		frappe.throw(_("The draft is not valid."))
	key = _key(doctype, name)
	if frappe.db.exists(DRAFT, key):
		frappe.db.set_value(DRAFT, key, "data", data)  # also bumps `modified`
	else:
		frappe.get_doc(
			{"doctype": DRAFT, "draft_key": key, "user": frappe.session.user, "ref_doctype": doctype, "ref_name": name, "data": data}
		).insert(ignore_permissions=True)
	return frappe.db.get_value(DRAFT, key, "modified")


@frappe.whitelist()
def get_draft(doctype, name=None):
	"""The signed-in user's draft of this form: {data, modified} or None."""
	name = name or ""
	_check_access(doctype, name)
	row = frappe.db.get_value(DRAFT, _key(doctype, name), ["data", "modified"], as_dict=True)
	return {"data": json.loads(row.data), "modified": row.modified} if row and row.data else None


@frappe.whitelist(methods=["POST"])
def delete_draft(doctype, name=None):
	"""Drop the signed-in user's draft (the record was saved, or the user chose to discard it)."""
	key = _key(doctype, name or "")
	if frappe.db.exists(DRAFT, key):
		frappe.delete_doc(DRAFT, key, ignore_permissions=True, force=True)
	return True


def clear_old_drafts():
	"""Daily: a draft nobody went back to is removed after DRAFT_DAYS."""
	frappe.db.delete(DRAFT, {"modified": ("<", add_days(now_datetime(), -DRAFT_DAYS))})
