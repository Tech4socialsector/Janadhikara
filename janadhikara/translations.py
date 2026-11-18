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
DATA_DIR = os.path.join(os.path.dirname(__file__), "translation_data")


# Every language the app has text for, by its own name. Which of them a site offers depends on its city.
LANGUAGES = {"en": "English", "as": "অসমীয়া", "hi": "हिन्दी", "te": "తెలుగు"}
DEFAULT_LANGUAGES = ("en", "as", "hi")  # a city without a pack of its own (Guwahati)


def offered_languages():
	"""The languages this site offers: its city's (pack "languages"), else English, Assamese and Hindi."""
	from janadhikara.city_pack import city_languages

	return [code for code in city_languages() if code in LANGUAGES]


def ensure_languages(restrict=False):
	"""Make sure the languages this site offers exist and are enabled (a new site may not have Assamese or Telugu
	at all); with restrict=True every other language is switched off."""
	offered = offered_languages()
	for code in offered:
		name = LANGUAGES[code]
		if frappe.db.exists("Language", code):
			frappe.db.set_value("Language", code, {"enabled": 1, "language_name": name})
		else:
			frappe.get_doc({"doctype": "Language", "language_code": code, "language_name": name, "enabled": 1}).insert(
				ignore_permissions=True
			)
	if restrict:
		frappe.db.set_value("Language", {"name": ["not in", offered]}, "enabled", 0)


def import_translations():
	"""Create the Translation records that are not there yet (existing ones are left as they are)."""
	ensure_languages()
	offered = set(offered_languages())
	rows = []
	for filename in sorted(os.listdir(DATA_DIR)):  # translations.json, and one file per extra language (translations_te.json)
		if filename.startswith("translations") and filename.endswith(".json"):
			with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
				rows += [row for row in json.load(f) if row["language"] in offered]  # only this city's languages
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
		try:
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
		except Exception:
			# one bad row must not stop the rest (or a migrate)
			frappe.log_error(title="Janadhikara: translation not imported", message=frappe.get_traceback())
	frappe.db.commit()
	return created


def _import_in_background():
	"""A site where the one-off import never ran (a fresh install skips patches, and not every deploy migrates):
	start it now, in the background, at most once every ten minutes."""
	key = "janadhikara_translation_import_started"
	if frappe.cache.get_value(key):
		return
	frappe.cache.set_value(key, 1, expires_in_sec=600)
	# one at a time: a second request while it is queued or running adds nothing (a busy queue also holds up a deploy's migrate)
	frappe.enqueue(
		"janadhikara.translations.import_translations", queue="long", timeout=1800,
		job_id="janadhikara_import_translations", deduplicate=True,
	)


@frappe.whitelist()
def get_app_translations(language):
	"""The app's translations for one language, shaped for the app: interface text by English sentence and
	questionnaire text by DocType and field. Only app text (not sensitive), readable by any signed-in user."""
	out = {"ui": {}, "heading": {}, "option": {}, "help": {}, "dpdp": {}, "fields": {}}
	if not language or language == "en" or language not in offered_languages():
		return out
	if not frappe.db.exists("Translation", {"language": language, "context": ["like", PREFIX + "%"]}):
		_import_in_background()
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
