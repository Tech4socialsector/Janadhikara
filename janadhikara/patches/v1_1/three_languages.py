import frappe

# The app is offered in English, Assamese and Hindi only for now.
KEEP = {"en": "English", "as": "অসমীয়া", "hi": "हिन्दी"}


def execute():
	for code, name in KEEP.items():
		if frappe.db.exists("Language", code):
			frappe.db.set_value("Language", code, {"enabled": 1, "language_name": name})
		else:
			frappe.get_doc({"doctype": "Language", "language_code": code, "language_name": name, "enabled": 1}).insert(
				ignore_permissions=True
			)
	frappe.db.set_value("Language", {"name": ["not in", list(KEEP)]}, "enabled", 0)
