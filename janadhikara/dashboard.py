"""Numbers behind the Dashboard page: the Settlement profiles.

Every query goes through frappe.get_list, so a user only ever counts the records they may read.
frontend/src/data/offlineDashboard.js works out the same numbers on the phone - keep the two in step."""

import calendar
from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint

from janadhikara.security import user_scope

SETTLEMENT = "Settlement"
STATUS_ORDER = ["Partially Completed", "Completed", "Revision Needed", "Validated"]

# key, title, fields added up over the settlements
TOTALS = [
	("households", "Households", ["s2_total_households"]),
	("population", "Population", ["s2_total_population"]),
	("migrant_households", "Migrant households", ["s2_migrant_household_count"]),
	("children_0_6", "Children aged 0-6", ["s2_children_0_3", "s2_children_3_6"]),
	("disability", "Persons with disabilities", ["s2_persons_with_disabilities"]),
]
# key, title, field, answer: settlements that gave that answer
ANSWER_CARDS = [
	("eviction_risk", "Settlements at risk of eviction", "s3_eviction_risk", "Yes"),
	("recommended", "Recommended for the program", "s10_recommended", "Yes"),
]
# key, title, field, kind ("donut" | "bar" | "hbar"), keep the field's option order
CHARTS = [
	("validation_status", "Profile status", "validation_status", "donut", True),
	("notified", "Notified status", "s1_notified", "donut", True),
	("category", "Category of settlement", "s1_category", "hbar", True),
	("land_type", "Government or private land", "s1_land_type", "donut", True),
	("zone", "Settlements by zone", "s1_zone", "hbar", False),
	("located_close_to", "Located close to", "s1_located_close_to", "hbar", True),
	("migrant_type", "Type of migrants", "s2_migrant_type", "donut", True),
	("recommended", "Recommended for the program", "s10_recommended", "donut", True),
]


@frappe.whitelist()
def get_filter_options():
	"""What the dashboard's filters can offer this user."""
	# Partner Details is an admin-only list (it holds the workers' contacts), so the names come from the user's own scope:
	# every partner for the programme team, just their own partner for anyone else.
	kind, own_partner = user_scope()
	if kind == "all":
		partners = frappe.get_all("Partner Details", fields=["name", "organization_name"], limit_page_length=0, order_by="organization_name")
	else:
		partners = [frappe._dict(name=own_partner, organization_name=frappe.db.get_value("Partner Details", own_partner, "organization_name"))] if own_partner else []
	return {
		"partners": [{"value": p.name, "label": p.organization_name or p.name} for p in partners],
		"zones": frappe.get_all("Municipal Zone", filters={"enabled": 1}, pluck="name", order_by="name"),
		"wards": frappe.get_all("Municipal Ward", filters={"enabled": 1}, pluck="name", order_by="name"),
		"categories": _select_options("s1_category"),
		"validation_statuses": _status_options(),
		# who may download the records behind a number (Frappe's own Export permission)
		"can_export": {SETTLEMENT: bool(frappe.has_permission(SETTLEMENT, "export"))},
	}


def _status_options():
	names = frappe.get_all("Validation Status", filters={"enabled": 1}, pluck="name")
	return [n for n in STATUS_ORDER if n in names] + sorted(n for n in names if n not in STATUS_ORDER)


def _select_options(fieldname):
	field = frappe.get_meta(SETTLEMENT).get_field(fieldname)
	return [o for o in (field.options or "").split("\n") if o] if field else []


def _counts(fieldname, filters):
	"""{answer: how many settlements}, blank answers left out."""
	rows = frappe.get_list(
		SETTLEMENT, filters=filters, fields=[fieldname, {"COUNT": "name", "as": "count"}], group_by=fieldname, limit_page_length=0
	)
	return {r[fieldname]: r["count"] for r in rows if r[fieldname] not in (None, "")}


def _rows(counts, filters, fieldname, order=None):
	"""Chart rows, each with the list filters that show its settlements."""
	keys = [k for k in order if counts.get(k)] + sorted(k for k in counts if k not in order) if order else sorted(counts, key=lambda k: -counts[k])
	return [{"label": k, "count": counts[k], "filters": {**filters, fieldname: k}} for k in keys]


@frappe.whitelist()
def get_dashboard(partner_organization=None, zone=None, ward=None, category=None, validation_status=None, from_date=None, to_date=None):
	filters = {}
	for field, value in (
		("partner_organization", partner_organization), ("s1_zone", zone), ("s1_ward", ward),
		("s1_category", category), ("validation_status", validation_status),
	):
		if value:
			filters[field] = value
	if from_date and to_date:
		filters["record_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["record_date"] = [">=", from_date]
	elif to_date:
		filters["record_date"] = ["<=", to_date]

	settlements = frappe.get_list(
		SETTLEMENT, filters=filters, limit_page_length=0,
		fields=["record_date", *dict.fromkeys(f for _, _, fields in TOTALS for f in fields)],
	)

	def card(key, title, value, card_filters, suffix=None):
		return {"key": key, "title": title, "value": value, "suffix": suffix, "doctype": SETTLEMENT, "filters": card_filters}

	cards = [card("settlements", "Settlements profiled", len(settlements), filters)]
	for key, title, fields in TOTALS:
		cards.append(card(key, title, sum(cint(s.get(f)) for s in settlements for f in fields), filters))
	for key, title, field, answer in ANSWER_CARDS:
		cards.append(card(key, title, _counts(field, filters).get(answer, 0), {**filters, field: answer}))

	charts = []
	for key, title, field, kind, ordered in CHARTS:
		order = (STATUS_ORDER if field == "validation_status" else _select_options(field)) if ordered else None
		charts.append({"key": key, "title": title, "kind": kind, "rows": _rows(_counts(field, filters), filters, field, order)})

	per_month = Counter(str(s.record_date)[:7] for s in settlements if s.record_date)
	monthly = []
	for month in sorted(per_month):
		year, mon = (int(x) for x in month.split("-"))
		last = calendar.monthrange(year, mon)[1]
		monthly.append({
			"month": month, "count": per_month[month],
			"filters": {**filters, "record_date": ["between", [f"{month}-01", f"{month}-{last:02d}"]]},
		})
	return {"cards": cards, "charts": charts, "monthly": monthly}


EXPORTABLE = (SETTLEMENT,)
EXPORT_LIMIT = 50000
STANDARD_COLUMNS = {"owner": "Created By", "creation": "Created On", "modified": "Last Modified"}
NOT_A_COLUMN = ("Section Break", "Column Break", "Tab Break", "Table", "Table MultiSelect", "HTML", "Button", "Image", "Password", "Attach", "Attach Image", "Geolocation")


def _exportable(doctype):
	"""The dashboard's doctype, and every doctype in the app's own navigation (its lists)."""
	if doctype in EXPORTABLE:
		return True
	from janadhikara.api import get_app_modules

	return any(item.get("doctype_name") == doctype for module in get_app_modules() for item in module.get("doctypes", []))


@frappe.whitelist()
def can_export(doctype):
	"""Whether the signed-in user may download this doctype's list (the list view shows Export only then)."""
	return bool(_exportable(doctype) and frappe.has_permission(doctype, "export"))


def _safe_cell(value):
	"""A spreadsheet runs a cell that starts with = + - @ as a formula; show it as text instead."""
	if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
		return "'" + value
	return value


@frappe.whitelist()
def export_records(doctype, filters=None, fields=None, order_by=None, search=None, file_format="csv"):
	"""Download the records behind a number or chart (every match, not just a page) with the chosen
	columns, as CSV or Excel. Needs Frappe's Export permission, and reads only what the user may read."""
	if not _exportable(doctype):
		frappe.throw(_("{0} cannot be exported.").format(doctype), frappe.PermissionError)
	frappe.has_permission(doctype, "export", throw=True)
	meta = frappe.get_meta(doctype)
	filters = frappe.parse_json(filters) or {}
	wanted = frappe.parse_json(fields) or ["name"]
	if wanted == "all":  # every field of the doctype, in form order
		wanted = ["name"] + [f.fieldname for f in meta.fields] + list(STANDARD_COLUMNS)
	columns = [
		f for f in wanted
		if f in STANDARD_COLUMNS or f == "name" or (meta.has_field(f) and meta.get_field(f).fieldtype not in NOT_A_COLUMN)
	] or ["name"]
	or_filters = None
	if search:
		title_field = meta.title_field or "name"
		or_filters = {"name": ["like", f"%{search}%"], title_field: ["like", f"%{search}%"]}
	rows = frappe.get_list(
		doctype, filters=filters, or_filters=or_filters, fields=columns, order_by=_safe_order(meta, order_by),
		limit_page_length=EXPORT_LIMIT,
	)
	labels = [
		_("ID") if f == "name" else _(STANDARD_COLUMNS[f]) if f in STANDARD_COLUMNS else _(meta.get_field(f).label or f)
		for f in columns
	]
	table = [labels] + [[_safe_cell(r.get(f)) for f in columns] for r in rows]
	filename = f"{frappe.scrub(doctype)}_{frappe.utils.nowdate()}"
	if file_format == "xlsx":
		from frappe.utils.xlsxutils import make_xlsx

		frappe.response["filecontent"] = make_xlsx(table, doctype).getvalue()
		frappe.response["filename"] = f"{filename}.xlsx"
	else:
		import csv
		import io

		out = io.StringIO()
		csv.writer(out).writerows(table)
		frappe.response["filecontent"] = ("\ufeff" + out.getvalue()).encode("utf-8")  # BOM: Excel reads Unicode
		frappe.response["filename"] = f"{filename}.csv"
	frappe.response["type"] = "binary"


def _safe_order(meta, order_by):
	"""`field asc|desc` for a real field, else newest first."""
	try:
		field, direction = (order_by or "").split()
	except ValueError:
		return "modified desc"
	if direction.lower() in ("asc", "desc") and (field in ("name", "modified", "creation") or meta.has_field(field)):
		return f"{field} {direction.lower()}"
	return "modified desc"
