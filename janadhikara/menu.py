"""Default App Module Settings (the sidebar of the Vue app).

Master Data: every doctype in the Masters module is listed in the "Master Data"
module automatically (after each migrate), so a new master never needs a manual
sidebar entry. Anything an admin already placed - or reordered, or removed from
the sidebar on purpose by deleting the row - is left alone only for rows that
exist; missing master doctypes are appended."""

import frappe

MASTERS = "Masters"
MASTER_LABEL = "Master Data"
MASTER_ICON = "database"

# Sidebar icon per doctype (Lucide names) and per module.
ITEM_ICONS = {
	"Settlement": "map-pin",
	"Household Profile": "house",
	"Individual Profile": "users",
	"Relationship Type": "heart-handshake",
	"Survey": "clipboard-list",
	"Partner Details": "building-2",
	"Announcement": "megaphone",
	"AI Guide Section": "book-open",
	"AI Guide Instruction": "book-open",
}
MODULE_ICONS = {
	"Engine": "user-cog",  # shown as "Administrator"
	"Records": "folder-open",
	"Baseline": "house",
	"Masters": "database",
}


def _get_or_create_setting(module_name, label, icon, sort_order):
	if frappe.db.exists("App Module Setting", module_name):
		return frappe.get_doc("App Module Setting", module_name)
	return frappe.get_doc(
		{
			"doctype": "App Module Setting",
			"module_name": module_name,
			"label": label,
			"icon": icon,
			"enabled": 1,
			"sort_order": sort_order,
		}
	)


def ensure_master_sidebar():
	"""after_migrate: Master Data lists every non-child doctype of the Masters module."""
	if not frappe.db.exists("DocType", "App Module Setting"):
		return
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": MASTERS, "istable": 0, "issingle": 0, "custom": 0},
		pluck="name",
		order_by="name asc",
	)
	if not doctypes:
		return
	setting = _get_or_create_setting(MASTERS, MASTER_LABEL, MASTER_ICON, 4)
	listed = {row.doctype_name for row in setting.doctypes or []}
	missing = [d for d in doctypes if d not in listed]
	if not missing and not setting.is_new():
		return
	for doctype in missing:
		setting.append(
			"doctypes", {"item_type": "Link", "doctype_name": doctype, "icon": ITEM_ICONS.get(doctype)}
		)
	setting.flags.ignore_permissions = True
	setting.save() if not setting.is_new() else setting.insert()
	frappe.db.commit()


def apply_icons():
	"""Give every module and sidebar item its icon (see ITEM_ICONS / MODULE_ICONS).
	Items for doctypes not listed keep what they have."""
	for name in frappe.get_all("App Module Setting", pluck="name"):
		setting = frappe.get_doc("App Module Setting", name)
		if name in MODULE_ICONS:
			setting.icon = MODULE_ICONS[name]
		for row in setting.doctypes or []:
			if row.item_type in (None, "Link") and row.doctype_name in ITEM_ICONS:
				row.icon = ITEM_ICONS[row.doctype_name]
		setting.flags.ignore_permissions = True
		setting.save()
	frappe.db.commit()
