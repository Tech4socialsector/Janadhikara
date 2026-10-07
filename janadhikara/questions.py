"""Questions from the Question Bank, asked on a form without adding fields to its doctype.

A doctype that can hold questions has one child table, "Question Answer" (a Table field whose
options is "Question Answer"). Each question is shown on the form like a field, but its answer is
one row in that table. This module serves the questions and checks the answers on save."""

import frappe
from frappe import _

ANSWERS_TABLE_DOCTYPE = "Question Answer"
CHOICE_TYPES = ("Select", "Multi-select")


def answers_fieldname(doctype):
	"""The doctype's Table field that holds the answers, or None if it can't hold questions."""
	for df in frappe.get_meta(doctype).get_table_fields():
		if df.options == ANSWERS_TABLE_DOCTYPE:
			return df.fieldname
	return None


ANSWERS_FIELDNAME = "question_answers"


def ensure_answers_table(doctype):
	"""Make `doctype` able to hold questions: if it has no "Question Answer" table yet, add one as a
	custom field at the end of the form. Returns the table's fieldname."""
	fieldname = answers_fieldname(doctype)
	if fieldname:
		return fieldname
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle:
		frappe.throw(_("{0} cannot hold questions - it is a child table or a single doctype.").format(frappe.bold(doctype)))
	if meta.has_field(ANSWERS_FIELDNAME):
		frappe.throw(
			_("{0} already has a field named {1} that is not a Question Answer table.").format(
				frappe.bold(doctype), frappe.bold(ANSWERS_FIELDNAME)
			)
		)
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": doctype,
			"fieldname": ANSWERS_FIELDNAME,
			"label": "Questions",
			"fieldtype": "Table",
			"options": ANSWERS_TABLE_DOCTYPE,
			"insert_after": meta.fields[-1].fieldname if meta.fields else None,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=doctype)
	return ANSWERS_FIELDNAME


QUESTION_FIELDS = [
	"name", "question_no", "question", "description", "answer_type", "options", "group_type", "section_group", "tab_group", "is_mandatory",
	"depends_on_question", "depends_on_operator", "depends_on_answer", "section_depends_on_question", "section_depends_on_answer",
	"show_if_doctype", "show_if_field", "show_if_operator", "show_if_value",
	"section_show_if_doctype", "section_show_if_field", "section_show_if_operator", "section_show_if_value",
]


@frappe.whitelist()
def get_questions(doctype: str):
	"""The enabled questions asked on `doctype`, in question-number order."""
	if not frappe.has_permission("Question Bank", "read"):
		return []
	return frappe.get_list(
		"Question Bank",
		filters={"for_doctype": doctype, "enabled": 1},
		fields=QUESTION_FIELDS,
		limit_page_length=1000,
	)


# ---- conditions ---------------------------------------------------------------
def _compare(actual, operator, expected):
	text = "" if actual is None else str(actual).strip()
	if operator == "is set":
		return bool(text)
	if operator == "is not set":
		return not text
	if operator == "contains":  # a multi-select answer is one choice per line
		return (expected or "").strip() in [line.strip() for line in text.splitlines()]
	if operator == "!=":
		return text != (expected or "")
	return text == (expected or "")


def _field_condition(question, prefix, doc, doctype):
	"""A 'display depends on' on a field of this form's doctype. A condition on another doctype
	cannot be checked here, so it does not hide the question."""
	cond_doctype = question.get(f"{prefix}_doctype")
	if not cond_doctype or cond_doctype != doctype:
		return True
	value = doc.get(question.get(f"{prefix}_field"))
	return _compare(value, question.get(f"{prefix}_operator") or "=", question.get(f"{prefix}_value"))


def is_shown(question, doc, answers):
	"""Is this question displayed for this record? (its own condition, its section's, and the
	'depends on another question' rule)"""
	if not _field_condition(question, "show_if", doc, doc.doctype):
		return False
	if not _field_condition(question, "section_show_if", doc, doc.doctype):
		return False
	if question.get("section_depends_on_question"):
		given = answers.get(question["section_depends_on_question"], "")
		if not _compare(given, "=", question.get("section_depends_on_answer")):
			return False
	if question.get("depends_on_question"):
		given = answers.get(question["depends_on_question"], "")
		if not _compare(given, question.get("depends_on_operator") or "=", question.get("depends_on_answer")):
			return False
	return True


# ---- saving -------------------------------------------------------------------------
def validate_answers(doc, method=None):
	"""On save: keep each answer row in step with its question, drop answers to questions that are
	no longer shown, and require the mandatory ones that are."""
	# Runs for every doctype (see hooks.py); Household Profile's own controller also calls it.
	if doc.flags.get("answers_validated") or doc.meta.istable or doc.meta.issingle:
		return
	if doc.meta.module not in ("Masters", "Common", "App Config", "Engine", "Baseline"):
		return  # questions only live on this app's own doctypes
	fieldname = answers_fieldname(doc.doctype)
	if not fieldname:
		return
	doc.flags.answers_validated = True
	questions = {q.name: q for q in get_questions_for_validation(doc.doctype)}
	rows = {}
	for row in doc.get(fieldname) or []:
		if row.question in questions:
			rows[row.question] = row
	answers = {name: (row.answer or "") for name, row in rows.items()}

	keep = []
	missing = []
	for name, q in sorted(questions.items(), key=lambda kv: str(kv[1].question_no)):
		shown = is_shown(q, doc, answers)
		row = rows.get(name)
		value = (row.answer if row else "") or ""
		if not shown:
			continue
		if q.is_mandatory and not value.strip():
			missing.append(f"{q.question_no}. {q.question}")
			continue
		if row and value.strip():
			if q.answer_type in CHOICE_TYPES:
				options = {o.strip() for o in (q.options or "").splitlines()}
				given = [v.strip() for v in value.splitlines() if v.strip()]
				if any(v not in options for v in given):
					frappe.throw(_("Question {0}: {1} is not one of the options.").format(q.question_no, frappe.bold(value)))
			row.update(
				{"question_no": q.question_no, "question_text": q.question, "answer_type": q.answer_type, "section_group": q.section_group}
			)
			keep.append(row)
	if missing:
		frappe.throw(_("Please answer: <br>{0}").format("<br>".join(missing)), title=_("Required questions"))
	doc.set(fieldname, keep)


def get_questions_for_validation(doctype):
	"""Every enabled question for the doctype (validation must see them even if the saving user's
	list permissions are narrower)."""
	return frappe.get_all("Question Bank", filters={"for_doctype": doctype, "enabled": 1}, fields=QUESTION_FIELDS)
