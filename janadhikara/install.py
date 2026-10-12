import frappe

from janadhikara.translations import ensure_languages, import_translations


def after_install():
	"""A fresh site skips one-off patches, so what they did for existing sites is done here:
	only English, Assamese and Hindi are offered, and the app's translations are loaded."""
	ensure_languages(restrict=True)
	import_translations()
	frappe.db.commit()
