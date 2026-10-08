"""App translations (Assamese, Hindi) kept as Frappe Translation records.

Every record carries a context starting with "janadhikara:" so it never touches Desk's own text:
  janadhikara:ui | heading | option | help | dpdp     interface text, keyed by the English sentence
  janadhikara:field:<DocType>:<fieldname>:label | description | option    questionnaire text

The Translation list in Desk is the place to edit wording. import_translations() only adds what is
missing, so edits are never overwritten.
"""
import json
import os

import frappe

PREFIX = "janadhikara:"
DATA_FILE = os.path.join(os.path.dirname(__file__), "translation_data", "translations.json")


def import_translations():
	"""Create the Translation records that are not there yet (existing ones are left as they are)."""
	with open(DATA_FILE, encoding="utf-8") as f:
		rows = json.load(f)
	existing = {
		(r.language, r.context, r.source_text)
		for r in frappe.get_all(
			"Translation", filters={"context": ["like", PREFIX + "%"]}, fields=["language", "context", "source_text"], limit_page_length=0
		)
	}
	created = 0
	for row in rows:
		if (row["language"], row["context"], row["source"]) in existing:
			continue
		frappe.get_doc(
			{
				"doctype": "Translation",
				"language": row["language"],
				"context": row["context"],
				"source_text": row["source"],
				"translated_text": row["text"],
			}
		).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	return created


@frappe.whitelist()
def get_app_translations(language):
	"""The app's translations for one language, shaped for the app: interface text by English sentence and
	questionnaire text by DocType and field. Only app text (not sensitive), readable by any signed-in user."""
	out = {"ui": {}, "heading": {}, "option": {}, "help": {}, "dpdp": {}, "fields": {}}
	if not language or language == "en":
		return out
	for r in frappe.get_all(
		"Translation",
		filters={"language": language, "context": ["like", PREFIX + "%"]},
		fields=["source_text", "translated_text", "context"],
		limit_page_length=0,
	):
		kind = r.context[len(PREFIX) :]
		if kind in out and kind != "fields":
			out[kind][r.source_text] = r.translated_text
		elif kind.startswith("field:"):
			_, doctype, fieldname, part = kind.split(":", 3)
			entry = out["fields"].setdefault(doctype, {}).setdefault(fieldname, {})
			if part == "option":
				entry.setdefault("options", {})[r.source_text] = r.translated_text
			else:
				entry[part] = r.translated_text
	return out
