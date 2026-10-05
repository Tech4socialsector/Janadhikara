import frappe

from janadhikara.menu import ensure_master_sidebar


def _replace_items(setting, items):
	setting.set("doctypes", [])
	for item in items:
		setting.append("doctypes", {"item_type": "Link", "child": 0, **item})
	setting.flags.ignore_permissions = True
	setting.save()


def execute():
	"""Sidebar modules:
	- Master Data: every Masters doctype (Relationship Type, Survey, ...)
	- Baseline: Settlement, Household Profile, Individual Profile
	- Administrator (was Engine): Partner Details"""
	ensure_master_sidebar()

	if frappe.db.exists("App Module Setting", "Baseline"):
		baseline = frappe.get_doc("App Module Setting", "Baseline")
		baseline.icon = "house"
		_replace_items(
			baseline,
			[
				{"doctype_name": "Settlement", "icon": "map-pin"},
				{"doctype_name": "Household Profile", "icon": "house"},
				{"doctype_name": "Individual Profile", "icon": "users"},
			],
		)

	# The "Administrator" module: Engine's settings (or one already labelled so).
	name = frappe.db.get_value("App Module Setting", {"label": "Administrator"}) or (
		"Engine" if frappe.db.exists("App Module Setting", "Engine") else None
	)
	if name:
		admin = frappe.get_doc("App Module Setting", name)
		admin.label = "Administrator"
		admin.icon = "user-cog"
		if not any(r.doctype_name == "Partner Details" for r in admin.doctypes or []):
			admin.append("doctypes", {"item_type": "Link", "doctype_name": "Partner Details", "icon": "building"})
		admin.flags.ignore_permissions = True
		admin.save()
	frappe.db.commit()
