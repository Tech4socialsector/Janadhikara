"""Reference data for working without a connection.

`get_offline_pack` returns the field data a person needs to fill forms with no signal:
every record of the masters and linked doctypes behind the forms they can open (names and
titles for the Link pickers, plus their fields for cascading filters), and the records
of the app's own doctypes for looking things up. Field data only - never files, images,
signatures, passwords, or the fields the AI Data Policy marks confidential - and only what the signed-in user may read. The sensitive
child tables (health, entitlements, documents, education) are left out.

The shape is columnar ({ columns, rows: [[...]] }) so it compresses well on the device."""

import frappe
from frappe.utils import now_datetime

MAX_ROWS = 5000
APP_MODULES = ("Masters", "App Config", "Engine", "Baseline")

# Held back from the device whatever the permissions say.
EXCLUDED = {"Role", "Entitlement", "Individual Document", "Health Condition", "Education Record", "Push Subscription", "ToDo"}

STORABLE = {
	"Data", "Select", "Link", "Dynamic Link", "Int", "Float", "Currency", "Percent", "Check", "Date", "Datetime",
	"Time", "Small Text", "Text", "Phone", "Autocomplete", "Read Only", "Rating", "Duration",
}


def _confidential_fields(doctype):
	"""Fields kept off the device: the ones the AI Data Policy marks Hidden (addresses, contact
	numbers, birth dates, income...). A look-up copy does not need them."""
	if not frappe.db.exists("AI Data Policy", doctype):
		return set()
	return {
		row.policy_field
		for row in frappe.get_doc("AI Data Policy", doctype).field_rules
		if row.handling == "Hidden"
	}


def _columns(meta):
	skip = _confidential_fields(meta.name)
	cols = [
		df.fieldname
		for df in meta.fields
		if df.fieldtype in STORABLE
		and not df.hidden
		and df.fieldname not in skip
		and not (df.fieldtype == "Data" and df.options in ("Phone", "Email"))
		and df.fieldtype != "Phone"
	]
	if meta.title_field and meta.title_field not in cols:
		cols.append(meta.title_field)
	return cols


def _linked_doctypes(meta):
	return [df.options for df in meta.fields if df.fieldtype == "Link" and df.options]


def _rows_for(doctype, meta, columns):
	if meta.istable:
		parent_doctype = frappe.db.get_value("DocField", {"options": doctype, "fieldtype": "Table"}, "parent")
		if not parent_doctype or not frappe.has_permission(parent_doctype, "read"):
			return None, []
		readable = set(frappe.get_list(parent_doctype, pluck="name", limit_page_length=MAX_ROWS))
		fields = ["name", "parent", *columns]
		rows = frappe.get_all(
			doctype, filters={"parenttype": parent_doctype}, fields=fields, limit_page_length=MAX_ROWS
		)
		rows = [r for r in rows if r.parent in readable]
		return ["name", "parent", *columns], rows

	if not frappe.has_permission(doctype, "read"):
		return None, []
	fields = ["name", *columns]
	return fields, frappe.get_list(doctype, fields=fields, order_by="modified desc", limit_page_length=MAX_ROWS)


def _user_pack():
	"""Users as a picker needs them: id and name only. A partner worker gets only the people of their own
	partner organisation (never the whole user list); the programme team gets everyone."""
	from janadhikara.security import user_scope

	filters = {"enabled": 1, "user_type": "System User"}
	kind, partner = user_scope()
	if kind == "partner":
		workers = frappe.get_all("Employee", filters={"parenttype": "Partner Details", "parent": partner}, fields=["user", "email"])
		allowed = {frappe.session.user} | {w.user for w in workers if w.user} | {w.email for w in workers if w.email}
		filters["name"] = ["in", list(allowed)]
	elif kind == "none":
		filters["name"] = frappe.session.user
	rows = frappe.get_all("User", filters=filters, fields=["name", "full_name"], limit_page_length=MAX_ROWS)
	return {"title_field": "full_name", "istable": 0, "columns": ["name", "full_name"], "rows": [[r.name, r.full_name] for r in rows]}


@frappe.whitelist()
def get_offline_pack():
	from janadhikara.api import get_app_modules

	seeds = []
	for module in get_app_modules():
		seeds += [item["doctype_name"] for item in module.get("doctypes", []) if item.get("doctype_name")]

	wanted, queue = [], list(dict.fromkeys(seeds))
	while queue:
		doctype = queue.pop(0)
		if doctype in wanted or doctype in EXCLUDED or not frappe.db.exists("DocType", doctype):
			continue
		wanted.append(doctype)
		meta = frappe.get_meta(doctype)
		if meta.module in APP_MODULES:  # follow links out of the app's own doctypes only (not through User, Role...)
			queue += [d for d in _linked_doctypes(meta) if d not in wanted]
			queue += [df.options for df in meta.fields if df.fieldtype in ("Table", "Table MultiSelect") and df.options]

	pack = {}
	for doctype in wanted:
		if doctype == "User":
			pack["User"] = _user_pack()
			continue
		meta = frappe.get_meta(doctype)
		if meta.issingle:
			continue
		columns = _columns(meta)
		fields, rows = _rows_for(doctype, meta, columns)
		if fields is None:
			continue
		pack[doctype] = {
			"title_field": meta.title_field,
			"istable": 1 if meta.istable else 0,
			"columns": fields,
			"rows": [[row.get(f) if not hasattr(row.get(f), "isoformat") else str(row.get(f)) for f in fields] for row in rows],
		}
	return {
		"version": 1,
		"generated": str(now_datetime()),
		"user": frappe.session.user,
		"doctypes": pack,
		# Form layouts to keep for offline use: this app's own doctypes only (never User, Role...).
		"meta_doctypes": _app_meta_doctypes(),
	}


def _app_meta_doctypes():
	"""The app's own doctypes whose form layout the signed-in user may need: those they can
	read, plus the child tables of those (their field definitions, not any data)."""
	names = frappe.get_all(
		"DocType", filters={"module": ["in", APP_MODULES], "custom": 0, "issingle": 0}, pluck="name"
	)
	readable = [
		d
		for d in names
		if d != "Push Subscription" and not frappe.get_meta(d).istable and frappe.has_permission(d, "read")
	]
	children = set()
	for d in readable:
		for df in frappe.get_meta(d).fields:
			if df.fieldtype in ("Table", "Table MultiSelect") and df.options in names:
				children.add(df.options)
	return sorted({*readable, *children})


# ---- Uploads from the phone (always started by the person, from Sync Data) --------------------------------------

LOG = "Offline Sync Log"
RECORD_DOCTYPES = ("Settlement", "Household Profile", "Individual Profile")
FILE_FIELDTYPES = {"Attach", "Attach Image", "Signature", "Image"}
SKIP_TABLES = {"Individual Document"}  # attachments: never put on a device
IGNORED_KEYS = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "parent", "parentfield", "parenttype", "doctype", "__islocal", "__unsaved"}


def _check_doctype(doctype):
	if doctype in EXCLUDED or not frappe.db.exists("DocType", doctype):
		frappe.throw(f"{doctype} cannot be uploaded from a device.", frappe.PermissionError)
	meta = frappe.get_meta(doctype)
	if meta.module not in APP_MODULES or meta.istable or meta.issingle or meta.custom:
		frappe.throw(f"{doctype} cannot be uploaded from a device.", frappe.PermissionError)
	return meta


def _earlier(client_id):
	"""The result of an earlier upload with this id (the reply never reached the phone), if any."""
	if not client_id:
		frappe.throw("Missing upload id.")
	row = frappe.db.get_value(LOG, client_id, ["reference_doctype", "reference_name"], as_dict=True)
	if row:
		return {"status": "ok", "doctype": row.reference_doctype, "name": row.reference_name, "duplicate": 1}


def _log(client_id, action, doctype, name):
	frappe.get_doc(
		{"doctype": LOG, "client_id": client_id, "action": action, "reference_doctype": doctype,
		 "reference_name": name, "synced_by": frappe.session.user}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def push_insert(client_id, doc):
	"""Create a record saved offline. Sending the same client_id again returns the first result."""
	doc = frappe.parse_json(doc)
	earlier = _earlier(client_id)
	if earlier:
		return earlier
	_check_doctype(doc.get("doctype"))
	doc.pop("name", None)
	new = frappe.get_doc(doc)
	new.insert()
	_log(client_id, "Insert", new.doctype, new.name)
	return {"status": "ok", "doctype": new.doctype, "name": new.name}


def _plain(value):
	"""A value as it is compared between the phone's copy and the server's: child rows without their ids."""
	if isinstance(value, (list, tuple)):
		return [_plain(v) for v in value]
	if isinstance(value, dict):
		return {k: _plain(v) for k, v in value.items() if k not in IGNORED_KEYS}
	if hasattr(value, "as_dict"):
		return _plain(value.as_dict())
	if hasattr(value, "isoformat") or hasattr(value, "total_seconds"):
		return str(value)
	if value in (None, ""):
		return None
	return value


@frappe.whitelist(methods=["POST"])
def push_update(client_id, doctype, name, changes, base=None, base_modified=None, force=0):
	"""Apply the fields changed offline to an existing record. If someone changed one of those same
	fields on the server since the phone's copy was taken, nothing is saved and the clashing fields are
	returned ({"status": "conflict"}) so the person can choose; force=1 keeps the phone's values."""
	changes, base = frappe.parse_json(changes) or {}, frappe.parse_json(base) or {}
	earlier = _earlier(client_id)
	if earlier:
		return earlier
	_check_doctype(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	meta = frappe.get_meta(doctype)

	if not int(force or 0) and base_modified and str(doc.modified) != str(base_modified):
		clashes = []
		for fieldname in changes:
			if _plain(doc.get(fieldname)) != _plain(base.get(fieldname)):
				df = meta.get_field(fieldname)
				clashes.append(
					{"fieldname": fieldname, "label": df.label if df else fieldname, "mine": changes[fieldname], "server": _plain(doc.get(fieldname))}
				)
		if clashes:
			return {"status": "conflict", "fields": clashes, "modified": str(doc.modified)}

	for fieldname, value in changes.items():
		if fieldname in IGNORED_KEYS or not meta.has_field(fieldname):
			continue
		doc.set(fieldname, value)
	doc.save()
	_log(client_id, "Update", doctype, name)
	return {"status": "ok", "doctype": doctype, "name": name, "modified": str(doc.modified)}


# ---- "Download my records" -----------------------------------------------------------------------------

def _record_dict(doc):
	data = doc.as_dict(no_nulls=True, convert_dates_to_str=True)
	for df in doc.meta.fields:
		if df.fieldtype in FILE_FIELDTYPES:
			data.pop(df.fieldname, None)
		elif df.fieldtype == "Table" and df.options in SKIP_TABLES:
			data.pop(df.fieldname, None)
	return data


@frappe.whitelist()
def get_offline_records(since=None):
	"""The signed-in person's own Settlements, Household and Individual Profiles (what their role and
	partner organisation allow), with child tables, for viewing and editing with no connection. No files or
	photos. `names` lists every record they can still read, so the phone can drop the ones that went away."""
	records, names = {}, {}
	for doctype in RECORD_DOCTYPES:
		if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
			continue
		names[doctype] = frappe.get_list(doctype, pluck="name", limit_page_length=MAX_ROWS)
		filters = {"modified": [">", since]} if since else {}
		changed = frappe.get_list(doctype, filters=filters, pluck="name", order_by="modified asc", limit_page_length=MAX_ROWS)
		records[doctype] = [_record_dict(frappe.get_doc(doctype, n)) for n in changed]
	return {"version": 1, "generated": str(now_datetime()), "user": frappe.session.user, "incremental": bool(since), "records": records, "names": names}
