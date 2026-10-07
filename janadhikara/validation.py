"""Field-level validation for every Janadhikara doctype (and their child rows).

One place, driven by field type and name, so a new doctype gets the same
checks without its own code. Runs on every save - form, offline sync, import
or API - so the rules can't be skipped by a hand-made request.
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowtime, today

APP_MODULES = {"Masters", "Common", "App Config", "Engine", "Baseline"}

MOBILE_RE = re.compile(r"^\d{10}$")
PINCODE_RE = re.compile(r"^[1-9]\d{5}$")
PERSON_NAME_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-][^\W\d_]+)*\.?$")

PERSON_NAME_FIELDS = {
	"member_name",
	"respondent_name",
	"household_head_name",
	"contact_person",
	"worker_name",
	"employee_name",
	"surveyor_name",
}
# never in the future: things that already happened when the record is saved
PAST_DATE_FIELDS = {"record_date", "date_of_birth", "since", "consent_date", "consent_withdrawn_on"}
# (earlier field, later field)
DATE_ORDER = [
	("start_date", "end_date"),
]
# fieldname -> (min, max); None = open. Anything else numeric just can't be negative.
RANGES = {
	"latitude": (-90, 90),
	"longitude": (-180, 180),
	"age": (0, 120),
	"head_age": (0, 120),
	"stay_months": (0, 11),
	"stay_years": (0, 120),
	"year": (1900, None),
	"q18_1_2_how_many_hours_they_get": (0, 24),
	"q16_1_2_proportion_children_going_private_school": (0, 100),
	"q16_1_3_proportion_children_going_government_sch": (0, 100),
	"q16_1_4_proportion_children_going_government_aid": (0, 100),
}
SIGNED_OK = {"latitude", "longitude"}


def resolve_default_tokens(doc, method=None):
	"""A form may send a field's default keyword ("Now", "Today") as it is: turn it into the real
	date or time before the record is written."""
	meta = frappe.get_meta(doc.doctype)
	if meta.module not in APP_MODULES:
		return
	for df in meta.fields:
		value = doc.get(df.fieldname)
		if value == "Now" and df.fieldtype == "Time":
			doc.set(df.fieldname, nowtime())
		elif value == "Now" and df.fieldtype == "Datetime":
			doc.set(df.fieldname, now_datetime())
		elif value == "Today" and df.fieldtype in ("Date", "Datetime"):
			doc.set(df.fieldname, today())


def validate_doc(doc, method=None):
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	meta = frappe.get_meta(doc.doctype)
	if meta.module not in APP_MODULES or meta.issingle and doc.doctype == "DocType":
		return
	errors = []
	_check(doc, meta, errors, parent=True)
	for table in meta.get_table_fields():
		child_meta = frappe.get_meta(table.options)
		for row in doc.get(table.fieldname) or []:
			_check(row, child_meta, errors, parent=False, row_label=f"{_(table.label)} #{row.idx}")
	if errors:
		frappe.throw("<br>".join(f"• {e}" for e in errors), title=_("Please correct the following"))


def _check(doc, meta, errors, parent, row_label=None):
	prefix = f"{row_label}: " if row_label else ""
	values = {}
	for df in meta.fields:
		fn, ft = df.fieldname, df.fieldtype
		if df.hidden or ft in ("Table", "Table MultiSelect", "Section Break", "Column Break", "Tab Break"):
			continue
		value = doc.get(fn)

		if ft in ("Attach", "Attach Image") and isinstance(value, str) and value and not re.match(r"^(/files/|/private/files/|https?://)", value):
			errors.append(prefix + _("{0} must be an uploaded file or a web address.").format(_(df.label or fn)))
			continue

		if ft == "Data" and isinstance(value, str):
			cleaned = " ".join(value.split())
			if cleaned != value:
				doc.set(fn, cleaned)
			value = cleaned
		if value in (None, ""):
			continue
		values[fn] = value
		label = _(df.label or fn)

		if ft == "Data" and df.options == "Phone" or fn in ("mobile_number", "contact_number") and ft == "Data":
			digits = re.sub(r"[\s\-()]", "", str(value))
			digits = re.sub(r"^(\+?91|0)(?=\d{10}$)", "", digits)
			if not MOBILE_RE.match(digits):
				errors.append(prefix + _("{0} must be a 10-digit number.").format(label))
		elif fn in PERSON_NAME_FIELDS and ft == "Data":
			if len(str(value)) < 2 or not PERSON_NAME_RE.match(str(value)):
				errors.append(prefix + _("{0} can only have letters, spaces, . ' and -.").format(label))
		elif fn in ("pincode", "pin_code") and ft == "Data":
			if not PINCODE_RE.match(str(value)):
				errors.append(prefix + _("{0} must be a valid 6-digit PIN code.").format(label))
		elif ft in ("Int", "Float", "Currency", "Percent"):
			num = flt(value)
			low, high = RANGES.get(fn, (None if fn in SIGNED_OK else 0, 100 if ft == "Percent" else None))
			if ft == "Percent":
				low, high = (0, 100)
			if low is not None and num < low or high is not None and num > high:
				errors.append(prefix + _range_message(label, low, high))
		elif ft in ("Date", "Datetime") and fn in PAST_DATE_FIELDS:
			if not parent or doc.is_new() or doc.has_value_changed(fn):
				as_date = getdate(value)
				if as_date > getdate(today()) or ft == "Datetime" and as_date == getdate(today()) and value > now_datetime():
					errors.append(prefix + _("{0} can't be in the future.").format(label))
				elif as_date.year < 1900:
					errors.append(prefix + _("{0} is not a valid date.").format(label))

	for first, later in DATE_ORDER:
		if first in values and later in values and getdate(values[later]) < getdate(values[first]):
			errors.append(
				prefix
				+ _("{0} can't be before {1}.").format(_(meta.get_label(later)), _(meta.get_label(first)))
			)


def _range_message(label, low, high):
	if low is not None and high is not None:
		return _("{0} must be between {1} and {2}.").format(label, cint(low), cint(high))
	if low is not None:
		return _("{0} can't be less than {1}.").format(label, cint(low))
	return _("{0} can't be more than {1}.").format(label, cint(high))


# --- Conditional questions (Settlement and Household Profile) -------------------------------
# A question hidden by its "show only if" holds no answer, and a question the form shows as mandatory
# can't be left empty. The same simple conditions the form evaluates, evaluated again on save.
_EQ = re.compile(r'^eval:doc\.(\w+)\s*==\s*"([^"]*)"$')
_PART_EQ = re.compile(r'^doc\.(\w+)\s*==\s*"([^"]*)"$')
_NE = re.compile(r'^eval:doc\.(\w+)\s*&&\s*doc\.\1\s*!=\s*"([^"]*)"$')
_HAS = re.compile(r'^\(doc\.(\w+)\|\|""\)\.split\(.*\)\.includes\("([^"]*)"\)$')
_SOME = re.compile(r'^\(doc\.(\w+)\|\|\[\]\)\.some\(r=>r\.(\w+)=="([^"]*)"\)$')


def _part_met(doc, part):
	if m := _PART_EQ.match(part):
		return doc.get(m.group(1)) == m.group(2)
	if m := _HAS.match(part):
		return m.group(2) in [v.strip() for v in str(doc.get(m.group(1)) or "").split("\n")]
	if m := _SOME.match(part):
		return any(row.get(m.group(2)) == m.group(3) for row in doc.get(m.group(1)) or [])
	return True  # a form the server doesn't know counts as shown


def condition_met(doc, expression):
	if not expression:
		return True
	if m := _NE.match(expression):
		return bool(doc.get(m.group(1))) and doc.get(m.group(1)) != m.group(2)
	if m := _EQ.match(expression):
		return doc.get(m.group(1)) == m.group(2)
	if expression.startswith("eval:"):
		return all(_part_met(doc, part.strip()) for part in expression[5:].split(" && "))
	return True


def clear_hidden_answers(doc):
	"""Drop answers to hidden questions. Walks the fields in order, so a cleared answer also hides
	whatever depended on it."""
	tab_ok = section_ok = True
	for df in doc.meta.fields:
		shown = condition_met(doc, df.depends_on)
		if df.fieldtype == "Tab Break":
			tab_ok, section_ok = shown, True
			continue
		if df.fieldtype == "Section Break":
			section_ok = shown
			continue
		if df.fieldtype in ("Column Break", "Table"):
			continue
		if not (tab_ok and section_ok and shown) and doc.get(df.fieldname) not in (None, "", 0, []):
			doc.set(df.fieldname, [] if df.fieldtype == "Table MultiSelect" else None)


def require_shown_answers(doc):
	"""A question the form shows as mandatory (mandatory_depends_on holds) can't be left empty. Questions
	in a hidden tab or section are not asked."""
	missing = []
	tab_ok = section_ok = True
	for df in doc.meta.fields:
		if df.fieldtype == "Tab Break":
			tab_ok, section_ok = condition_met(doc, df.depends_on), True
			continue
		if df.fieldtype == "Section Break":
			section_ok = condition_met(doc, df.depends_on)
			continue
		if (
			tab_ok
			and section_ok
			and df.mandatory_depends_on
			and condition_met(doc, df.depends_on)
			and condition_met(doc, df.mandatory_depends_on)
			and doc.get(df.fieldname) in (None, "", [])
		):
			missing.append(_(df.label))
	if missing:
		frappe.throw("<br>".join(f"• {label}" for label in missing), title=_("Please answer the following"))
