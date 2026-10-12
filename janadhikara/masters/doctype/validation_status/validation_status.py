# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

"""Validation Status: the options for a household's validation (Revision Needed, Validated...).

Each status can list the roles it is for. Empty = everyone. This is enforced on the server (list
queries and single-record checks), so the dropdown, the API and a hand-made request all agree."""

import frappe
from frappe.model.document import Document

SEES_ALL = {"Administrator", "System Manager", "Program Coordinator"}


class ValidationStatus(Document):
	pass


def _sees_all(user):
	return user == "Administrator" or bool(set(frappe.get_roles(user)) & SEES_ALL)


def get_permission_query_conditions(user=None):
	"""Lists (and the Link picker) only return statuses the user may use."""
	user = user or frappe.session.user
	if _sees_all(user):
		return None
	roles = ", ".join(frappe.db.escape(r) for r in frappe.get_roles(user)) or "''"
	return f"""(
		`tabValidation Status`.enabled = 1
		and (
			not exists (select 1 from `tabValidation Status Role` vr
				where vr.parent = `tabValidation Status`.name and vr.parenttype = 'Validation Status')
			or exists (select 1 from `tabValidation Status Role` vr
				where vr.parent = `tabValidation Status`.name and vr.parenttype = 'Validation Status'
				and vr.role in ({roles}))
		)
	)"""


def is_usable_by(status_name, user=None):
	"""Can this user pick this status? (Used when a record is saved with it.)"""
	user = user or frappe.session.user
	if not status_name or _sees_all(user):
		return True
	row = frappe.db.get_value("Validation Status", status_name, "enabled")
	if not row:
		return False
	allowed = set(
		frappe.get_all(
			"Validation Status Role", filters={"parent": status_name, "parenttype": "Validation Status"}, pluck="role"
		)
	)
	return not allowed or bool(allowed & set(frappe.get_roles(user)))


def has_permission(doc, ptype=None, user=None, **kwargs):
	"""Single-record check; only reading is narrowed by role (editing stays with the doctype's permissions)."""
	if ptype not in (None, "read", "select"):
		return None
	return True if is_usable_by(doc.name, user or frappe.session.user) else False


def check_status_change(doc):
	"""Save-time rule for a record's Status (validation_status): the new status must be one the user may use, and a
	record that is Validated can only be moved by someone who may use Validated."""
	import frappe
	from frappe import _

	status = doc.get("validation_status")
	if not status or not (doc.is_new() or doc.has_value_changed("validation_status")):
		return
	if not is_usable_by(status):
		frappe.throw(_("You can't set the status {0}.").format(frappe.bold(status)), frappe.PermissionError)
	before = doc.get_doc_before_save()
	if before and before.get("validation_status") == "Validated" and not is_usable_by("Validated"):
		frappe.throw(_("This record is Validated: only a coordinator can change its status."), frappe.PermissionError)
