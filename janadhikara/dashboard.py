"""Numbers behind the Dashboard page.

Every query goes through frappe.get_list, so a user only ever counts the records they may read.
The filters narrow both Household Profile and Individual Profile; the settlement and partner
organisation of an individual are the ones stored from their household."""

import calendar
from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint

HOUSEHOLD = "Household Profile"
INDIVIDUAL = "Individual Profile"

AGE_GROUPS = [("0-5", 0, 5), ("6-14", 6, 14), ("15-17", 15, 17), ("18-35", 18, 35), ("36-59", 36, 59), ("60+", 60, 200)]
# Individual Profile question -> label, for "how many have it"
DOCUMENTS = [
	("doc_aadhaar", "Aadhaar"), ("doc_ration_card", "Ration card"), ("doc_voter_id", "Voter ID"),
	("doc_bank_account", "Bank account"), ("doc_pan", "PAN"), ("doc_birth_certificate", "Birth certificate"),
	("doc_eshram", "E-Shram"), ("doc_income_certificate", "Income certificate"),
]


@frappe.whitelist()
def get_filter_options():
	"""What the dashboard's filters can offer this user."""
	settlements = frappe.get_list("Settlement", fields=["name", "settlement_name"], limit_page_length=0, order_by="settlement_name")
	partners = frappe.get_list("Partner Details", fields=["name"], limit_page_length=0, order_by="name")
	return {
		"settlements": [{"value": s.name, "label": s.settlement_name or s.name} for s in settlements],
		"partners": [{"value": p.name, "label": p.name} for p in partners],
		"genders": ["Female", "Male", "Other"],
		"documentation_statuses": ["Partially Completed", "Completed"],
		"age_groups": [g[0] for g in AGE_GROUPS],
		"household_statuses": _select_options(HOUSEHOLD, "household_status"),
		"validation_statuses": frappe.get_all("Validation Status", filters={"enabled": 1}, pluck="name", order_by="name"),
		# who may download the records behind a number (Frappe's own Export permission)
		"can_export": {d: bool(frappe.has_permission(d, "export")) for d in (HOUSEHOLD, INDIVIDUAL)},
	}


def _select_options(doctype, fieldname):
	options = frappe.get_meta(doctype).get_field(fieldname).options or ""
	return [o for o in options.split("\n") if o]


def _date_field(doctype):
	"""The date a record is counted on: its Date, or - where the form has none - when it was created."""
	return "record_date" if frappe.get_meta(doctype).has_field("record_date") else "creation"


def _date_filter(doctype, filters, from_date, to_date):
	field = _date_field(doctype)
	if from_date and to_date:
		filters[field] = ["between", [from_date, to_date]]
	elif from_date:
		filters[field] = [">=", from_date]
	elif to_date:
		filters[field] = ["<=", to_date]


def _counts(doctype, fieldname, filters):
	"""{answer: how many records}, blank answers left out."""
	rows = frappe.get_list(
		doctype, filters=filters, fields=[fieldname, {"COUNT": "name", "as": "count"}], group_by=fieldname, limit_page_length=0
	)
	return {r[fieldname]: r["count"] for r in rows if r[fieldname] not in (None, "")}


def _series(counts, order=None, filters=None, fieldname=None):
	"""Chart rows. With `fieldname`, each row also carries the list filters that show its records."""
	keys = order or sorted(counts, key=lambda k: -counts[k])
	return [
		{"label": k, "count": counts.get(k, 0), **({"filters": {**filters, fieldname: k}} if fieldname else {})}
		for k in keys
		if counts.get(k, 0) or order
	]


def _month_filters(doctype, filters, month):
	"""The list filters for one `YYYY-MM`: that month replaces any date range."""
	year, mon = (int(x) for x in month.split("-"))
	last = calendar.monthrange(year, mon)[1]
	return {**filters, _date_field(doctype): ["between", [f"{month}-01", f"{month}-{last:02d}"]]}


def _total(doctype, filters):
	return cint(frappe.get_list(doctype, filters=filters, fields=[{"COUNT": "name", "as": "count"}])[0]["count"])


def _monthly(doctype, filters):
	field = _date_field(doctype)
	dates = frappe.get_list(doctype, filters=filters, fields=[field], limit_page_length=0, pluck=field)
	per_month = Counter(str(d)[:7] for d in dates if d)
	return per_month


@frappe.whitelist()
def get_dashboard(
	settlement=None, partner_organization=None, from_date=None, to_date=None, gender=None, documentation_status=None,
	age_group=None, household_status=None, validation_status=None,
):
	hh = {}
	ind = {}
	if settlement:
		hh["settlement"] = settlement
		ind["settlement_intervention_unit"] = settlement
	if partner_organization:
		hh["partner_organization"] = partner_organization
		ind["implementing_org"] = partner_organization
	_date_filter(HOUSEHOLD, hh, from_date, to_date)
	_date_filter(INDIVIDUAL, ind, from_date, to_date)
	if gender:
		ind["gender"] = gender
	if documentation_status:
		ind["documentation_status"] = documentation_status
	if validation_status:
		ind["validation_status"] = validation_status
	if household_status:
		hh["household_status"] = household_status
	for label, low, high in AGE_GROUPS:
		if label == age_group:
			ind["age"] = ["between", [low, high]]

	households = _total(HOUSEHOLD, hh)
	members = frappe.get_list(HOUSEHOLD, filters=hh, fields=[{"SUM": "member_count", "as": "members"}])[0]["members"]
	individuals = _total(INDIVIDUAL, ind)

	doc_status = _counts(INDIVIDUAL, "documentation_status", ind)
	validation = _counts(INDIVIDUAL, "validation_status", ind)
	completed = doc_status.get("Completed", 0)
	validated = validation.get("Validated", 0)

	ages = Counter()
	for age, count in _counts(INDIVIDUAL, "age", ind).items():
		for label, low, high in AGE_GROUPS:
			if low <= cint(age) <= high:
				ages[label] += count
	# children of school-going age who are not in school
	out_of_school = _total(INDIVIDUAL, {**ind, "out_of_school_status": ["is", "set"]})

	documents = []
	for fieldname, label in DOCUMENTS:
		answers = _counts(INDIVIDUAL, fieldname, ind)
		asked = sum(answers.values())
		have = answers.get("Yes", 0)
		documents.append({
			"label": label, "have": have, "asked": asked, "percent": round(100 * have / asked) if asked else 0,
			"filters": {**ind, fieldname: "Yes"},
		})

	hh_per_month, ind_per_month = _monthly(HOUSEHOLD, hh), _monthly(INDIVIDUAL, ind)
	months = sorted(set(hh_per_month) | set(ind_per_month))

	def card(key, title, value, doctype, filters, suffix=None):
		return {"key": key, "title": title, "value": value, "suffix": suffix, "doctype": doctype, "filters": filters}

	disability = _counts(INDIVIDUAL, "disability_in_family", ind).get("Yes", 0)
	women_not_working = _counts(INDIVIDUAL, "women_full_time_work", ind).get("No", 0)
	return {
		"cards": [
			card("households", "Households", households, HOUSEHOLD, hh),
			card("members", "Members (as told by households)", cint(members), HOUSEHOLD, hh),
			card("individuals", "Individual profiles", individuals, INDIVIDUAL, ind),
			card("completed", "Profiles completed", round(100 * completed / individuals) if individuals else 0, INDIVIDUAL, {**ind, "documentation_status": "Completed"}, "%"),
			card("validated", "Profiles validated", round(100 * validated / individuals) if individuals else 0, INDIVIDUAL, {**ind, "validation_status": "Validated"}, "%"),
			card("out_of_school", "Children out of school", out_of_school, INDIVIDUAL, {**ind, "out_of_school_status": ["is", "set"]}),
			card("disability", "Persons with disability", disability, INDIVIDUAL, {**ind, "disability_in_family": "Yes"}),
			card("women_not_working", "Women not in full-time work", women_not_working, INDIVIDUAL, {**ind, "women_full_time_work": "No"}),
		],
		"household_status": _series(_counts(HOUSEHOLD, "household_status", hh), filters=hh, fieldname="household_status"),
		"household_documentation": _series(_counts(HOUSEHOLD, "status", hh), filters=hh, fieldname="status"),
		"gender": _series(_counts(INDIVIDUAL, "gender", ind), filters=ind, fieldname="gender"),
		"age_groups": [
			{"label": label, "count": ages.get(label, 0), "filters": {**ind, "age": ["between", [low, high]]}}
			for label, low, high in AGE_GROUPS
		],
		"education": _series(_counts(INDIVIDUAL, "highest_education", ind), filters=ind, fieldname="highest_education"),
		"documentation": _series(doc_status, ["Partially Completed", "Completed"], ind, "documentation_status"),
		"documents": documents,
		"occupation": _series(_counts(INDIVIDUAL, "occupation_1", ind), filters=ind, fieldname="occupation_1")[:10],
		"monthly": [
			{
				"month": m, "Households": hh_per_month.get(m, 0), "Individuals": ind_per_month.get(m, 0),
				"household_filters": _month_filters(HOUSEHOLD, hh, m), "individual_filters": _month_filters(INDIVIDUAL, ind, m),
			}
			for m in months
		],
	}


EXPORTABLE = (HOUSEHOLD, INDIVIDUAL)
EXPORT_LIMIT = 50000
NOT_A_COLUMN = ("Section Break", "Column Break", "Tab Break", "Table", "Table MultiSelect", "HTML", "Button", "Image", "Attach", "Attach Image", "Geolocation")


def _safe_cell(value):
	"""A spreadsheet runs a cell that starts with = + - @ as a formula; show it as text instead."""
	if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
		return "'" + value
	return value


@frappe.whitelist()
def export_records(doctype, filters=None, fields=None, order_by=None, search=None, file_format="csv"):
	"""Download the records behind a number or chart (every match, not just a page) with the chosen
	columns, as CSV or Excel. Needs Frappe's Export permission, and reads only what the user may read."""
	if doctype not in EXPORTABLE:
		frappe.throw(_("{0} cannot be exported from the dashboard.").format(doctype), frappe.PermissionError)
	frappe.has_permission(doctype, "export", throw=True)
	meta = frappe.get_meta(doctype)
	filters = frappe.parse_json(filters) or {}
	columns = [
		f for f in (frappe.parse_json(fields) or ["name"])
		if f == "name" or (meta.has_field(f) and meta.get_field(f).fieldtype not in NOT_A_COLUMN)
	] or ["name"]
	or_filters = None
	if search:
		title_field = meta.title_field or "name"
		or_filters = {"name": ["like", f"%{search}%"], title_field: ["like", f"%{search}%"]}
	rows = frappe.get_list(
		doctype, filters=filters, or_filters=or_filters, fields=columns, order_by=_safe_order(meta, order_by),
		limit_page_length=EXPORT_LIMIT,
	)
	labels = [_("ID") if f == "name" else _(meta.get_field(f).label or f) for f in columns]
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
