"""The menu of the Vue app: App Module Group (one per Home card) and its items.

Every group is one Home card; its items are the DocTypes and pages in it. A group with "Show Sidebar" is one tile that
opens with a sidebar listing its items instead (Administration: partners, announcements and every master).

The standard groups are created once per site, with their items (ensure_module_groups). After that they belong to the
site's admins: nothing here overwrites an edit. Only the masters are kept up to date: every non-child doctype of the
Masters module (and of the site's city) is added to Administration after each migrate, so a new master never needs a
manual sidebar entry."""

import frappe

MASTERS = "Masters"
ADMIN = "Administration"

# the app's own pages: page name -> (address, icon)
PAGES = {
	"Dashboard": ("dashboard", "layout-dashboard"),
	"Worklist": ("worklist", "check-square"),
	"Support": ("support", "life-buoy"),
	"Help": ("help", "help-circle"),
	"Sync Data": ("sync-data", "cloud-upload"),
}
SYNC_ROLES = "ORW\nProgram Coordinator\nProgram Manager\nOrganization Admin"

# Sidebar icon per doctype (Lucide names)
ITEM_ICONS = {
	"Settlement": "map-pin",
	"HYD Settlement Profile": "map-pin",
	"HYD Household Profile": "house",
	"HYD Individual Profile": "users",
	"Household Profile": "house",
	"Individual Profile": "users",
	"Relationship Type": "heart-handshake",
	"Survey": "clipboard-list",
	"Partner Details": "building-2",
	"Announcement": "megaphone",
	"AI Guide Section": "book-open",
	"Validation Status": "badge-check",
	"Cooking Fuel": "flame",
	"Cluster": "network",
	"Question Bank": "list-checks",
	"AI Guide Instruction": "book-open",
}


def _doctype(name, label=None, icon=None):
	return {"item_type": "DocType", "doctype_name": name, "label": label, "icon": icon or ITEM_ICONS.get(name)}


def _page(name, roles=None):
	return {"item_type": "Page", "page": name, "roles": roles}


DATA = "Base Line"
PROGRAMME = "Dashboard & Reports"
# the names these two groups had in earlier releases (a site that already has them keeps them)
LEGACY = {DATA: ("Data Collection",), PROGRAMME: ("Programme Management",)}

# The Home page, in this order. name, description, icon, colour, sidebar?, items
GROUPS = [
	(ADMIN, "Manage partners, masters and announcements.", "user-cog", "Orange", 1,
		[_doctype("Partner Details", "Partner Profile"), _doctype("Announcement"), _doctype("AI Guide Section")]),
	(PROGRAMME, "Plan, assign and track field work.", "list-checks", "Green", 0,
		[_page("Dashboard"), _page("Worklist"), _page("Sync Data", SYNC_ROLES)]),
	(DATA, "Collect, manage and track programme data.", "clipboard-list", "Blue", 0,
		[_doctype("Settlement"), _doctype("Household Profile"), _doctype("Individual Profile")]),
	("Help & Support", "Get help, raise issues and track requests.", "life-buoy", "Purple", 0, [_page("Help"), _page("Support")]),
]
# where a module of the old App Module Setting went
OLD_MODULE_GROUP = {"Engine": ADMIN, "Masters": ADMIN, "Sync Data": PROGRAMME}


def find_group(name):
	"""The group called `name` - or, on a site that still has the earlier name, that one."""
	name = next((new for new, old in LEGACY.items() if name in old), name)  # an earlier name means the same group
	for candidate in (name, *LEGACY.get(name, ())):
		if frappe.db.exists("App Module Group", candidate):
			return candidate
	return None


def ensure_module_groups():
	"""after_migrate: on a site with no groups yet, create the standard ones (with their items). Once a site has groups
	they are its admins': a group renamed, changed or deleted is never recreated or touched."""
	if not frappe.db.exists("DocType", "App Module Group") or frappe.db.count("App Module Group"):
		return
	for order, (name, description, icon, color, sidebar, items) in enumerate(GROUPS, start=1):
		frappe.get_doc(
			{
				"doctype": "App Module Group", "group_name": name, "description": description, "icon": icon, "color": color,
				"sort_order": order, "enabled": 1, "use_sidebar": sidebar, "items": items,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()


def ensure_master_sidebar():
	"""after_migrate: Administration lists every non-child doctype of the Masters module (and of this site's city)."""
	admin = _admin_group()
	if not admin:
		return
	from janadhikara.city_pack import city_module, display_name, replacement_doctypes

	modules = [MASTERS] + ([city_module()] if city_module() else [])  # a city's own masters are listed on its site
	doctypes = frappe.get_all(
		"DocType",
		filters={"module": ["in", modules], "istable": 0, "issingle": 0, "custom": 0, "name": ["not in", ["HYD Settlement Profile", *replacement_doctypes()]]},
		pluck="name",
		order_by="name asc",
	)
	group = frappe.get_doc("App Module Group", admin)
	own = replacement_doctypes()

	def shown(doctype):
		"""A city doctype is listed and addressed without the city's short code ("HYD Municipal Ward" -> Municipal Ward)."""
		name = display_name(doctype)
		return (name, frappe.scrub(name).replace("_", "-")) if name != doctype else (None, None)

	changed = False
	# a city's replacement doctypes (its Settlement, Household, Individual Profile) sit with the others in their group, not here
	kept = [row for row in group.items or [] if not (row.item_type == "DocType" and row.doctype_name in own and row.doctype_name not in ("Partner Details",) and _is_master_row(row))]
	if len(kept) != len(group.items or []):
		group.set("items", kept)
		changed = True
	for row in group.items or []:
		if row.item_type != "DocType":
			continue
		label, route = shown(row.doctype_name or "")
		if label and (row.label, row.route) != (label, route):
			row.label, row.route, changed = label, route, True
	# a master the group already lists anywhere in the menu is not added again
	listed = {
		r.doctype_name
		for g in frappe.get_all("App Module Group", pluck="name")
		for r in frappe.get_doc("App Module Group", g).items or []
		if r.item_type == "DocType"
	}
	for doctype in doctypes:
		if doctype in listed:
			continue
		label, route = shown(doctype)
		group.append("items", {"item_type": "DocType", "doctype_name": doctype, "icon": ITEM_ICONS.get(doctype), "label": label, "route": route})
		changed = True
	if changed:
		group.flags.ignore_permissions = True
		group.save()
		frappe.db.commit()


def _admin_group():
	"""The group that lists the masters: Administration, or - if it was renamed - the first group with a sidebar."""
	if not frappe.db.exists("DocType", "App Module Group"):
		return None
	if frappe.db.exists("App Module Group", ADMIN):
		return ADMIN
	return frappe.db.get_value("App Module Group", {"use_sidebar": 1}, "name", order_by="sort_order asc")


def _is_master_row(row):
	"""A row Administration got only because it was a master (so it can be dropped when it becomes a city replacement)."""
	return row.doctype_name not in ("Partner Details", "Announcement", "AI Guide Section", "AI Guide Instruction")


def apply_icons():
	"""Give every sidebar item its icon (see ITEM_ICONS). Items for doctypes not listed keep what they have."""
	for name in frappe.get_all("App Module Group", pluck="name"):
		group = frappe.get_doc("App Module Group", name)
		for row in group.items or []:
			if row.item_type == "DocType" and row.doctype_name in ITEM_ICONS:
				row.icon = ITEM_ICONS[row.doctype_name]
		group.flags.ignore_permissions = True
		group.save()
	frappe.db.commit()


def dedupe_items():
	"""after_migrate: a group lists each DocType once. On a city's site an item for a shared doctype (Settlement) and one
	already pointing at the city's own (HYD Settlement Profile) are the same thing: keep the first, drop the repeats."""
	if not frappe.db.exists("DocType", "App Module Group"):
		return
	from janadhikara.city_pack import city_doctype

	for name in frappe.get_all("App Module Group", pluck="name"):
		group = frappe.get_doc("App Module Group", name)
		seen, keep = set(), []
		for row in group.items or []:
			if row.item_type == "DocType" and row.doctype_name:
				key = city_doctype(row.doctype_name)
				if key in seen:
					continue
				seen.add(key)
			keep.append(row)
		if len(keep) != len(group.items or []):
			group.set("items", keep)
			group.flags.ignore_permissions = True
			group.save()
	frappe.db.commit()
