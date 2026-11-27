"""City packs: how one city's questionnaire replaces a shared doctype on its site.

Every site runs the same app. A site's city (App Setting > City) picks a pack, city_packs/<city code>.json:

	{ "city": "hyderabad", "module": "Hyderabad", "prefix": "HYD", "replaces": { "Settlement": "HYD Settlement Profile" } }

`module` is the Frappe module (janadhikara/<module>/doctype/...) holding the city's own doctypes, `prefix` the short code
that starts their names (so two cities can both have a "Settlement Profile"), and `replaces` names the city doctype that
stands in for a shared one on that site. Applying a pack points the places that link to the shared doctype, and the
sidebar, at the city's. The prefix is never shown to the user: the sidebar, the address and the titles all use the name
without it. `hide` lists shared doctypes the city does not use (yet): they are left out of the menus, search and offline copy
of that site. Guwahati has no pack: it uses the shared doctypes as they are.

Applying only changes what still points at the shared doctype, so it is safe to run again (on every migrate)."""

import json
import os

import frappe

PACK_DIR = os.path.join(os.path.dirname(__file__), "city_packs")


def load_pack(city_code):
	"""The pack of a city, or None when the city has none."""
	if not city_code:
		return None
	path = os.path.join(PACK_DIR, f"{city_code}.json")
	if not os.path.isfile(path):
		return None
	with open(path) as f:
		return json.load(f)


def current_city_code():
	return frappe.db.get_single_value("App Setting", "city_code")


def current_pack():
	return load_pack(current_city_code())


def city_doctype(doctype):
	"""The doctype that does the job of `doctype` on this site: the city's own when its pack replaces it."""
	pack = current_pack()
	return (pack or {}).get("replaces", {}).get(doctype, doctype)


def hidden_doctypes():
	"""Doctypes this site's city does not use: left out of the sidebar, Home, search and the offline download. That is
	the pack's "hide" list plus every doctype of another city's module (a Guwahati site never shows PTN/HYD forms)."""
	from janadhikara.app_modules import CITY_MODULES

	pack = current_pack() or {}
	other_cities = [m for m in CITY_MODULES if m != pack.get("module")]
	others = frappe.get_all("DocType", filters={"module": ["in", other_cities]}, pluck="name") if other_cities else []
	return set(pack.get("hide", [])) | set(others)


def dashboard_spec():
	"""This city's own dashboard (pack "dashboard": filters, numbers and charts over its settlement profiles), or None
	for a city whose dashboard is the household and individual one."""
	filename = (current_pack() or {}).get("dashboard")
	if not filename:
		return None
	with open(os.path.join(PACK_DIR, filename)) as f:
		return json.load(f)


def replacement_doctypes():
	"""The city doctypes that stand in for shared ones (they belong in the module menus, not in Master Data)."""
	return set((current_pack() or {}).get("replaces", {}).values())


def city_languages():
	"""The languages this site offers (pack "languages"): English and Telugu on Hyderabad's site; English,
	Assamese and Hindi where the city has no pack of its own (Guwahati)."""
	from janadhikara.translations import DEFAULT_LANGUAGES

	return list((current_pack() or {}).get("languages") or DEFAULT_LANGUAGES)


def city_prefix():
	"""The short code that starts the names of this site's city doctypes (HYD), or None."""
	return (current_pack() or {}).get("prefix")


def display_name(doctype, prefix=None):
	"""A city doctype's name as users see it: without the city's short code ("HYD Settlement Profile" -> "Settlement Profile")."""
	prefix = prefix or city_prefix()
	return doctype[len(prefix) + 1 :] if prefix and doctype.startswith(prefix + " ") else doctype


def city_module():
	"""The module of this site's city doctypes, or None for a city without a pack."""
	return (current_pack() or {}).get("module")


def apply_city_pack(city_code=None):
	"""Make this site use its city's doctypes: Link fields and sidebar entries that point at a shared doctype
	are pointed at the city's one."""
	pack = load_pack(city_code or current_city_code())
	if not pack:
		return
	for shared, own in pack.get("replaces", {}).items():
		_repoint_links(shared, own)
		_swap_sidebar(shared, own, display_name(own, pack.get("prefix")))
	from janadhikara.menu import ensure_master_sidebar

	ensure_master_sidebar()  # the city's masters join Administration
	frappe.clear_cache()


def remove_city_pack(city_code):
	"""Undo apply_city_pack when the site's city changes: everything points at the shared doctypes again.
	Records already made on the city doctypes are kept."""
	pack = load_pack(city_code)
	if not pack:
		return
	for shared, own in pack.get("replaces", {}).items():
		_repoint_links(own, shared)
		_swap_sidebar(own, shared)
	_drop_master_links(pack)
	frappe.clear_cache()


def sync_city_packs():
	"""Make the site match its city: the city's pack is applied and every other city's is taken off, and only the
	city's languages are on. Runs after each migrate and whenever the city is changed, so the result never depends
	on what the site looked like before."""
	from janadhikara.translations import ensure_languages

	active = current_city_code()
	for filename in sorted(os.listdir(PACK_DIR)):
		code, ext = os.path.splitext(filename)
		if ext != ".json":
			continue
		if code == active:
			apply_city_pack(code)
		else:
			remove_city_pack(code)
	ensure_languages(restrict=True)


def _repoint_links(old, new):
	"""Every Link field of the app's doctypes that points at `old` is made to point at `new` (a Property
	Setter on its options, the same thing Customize Form writes). The doctypes `old` and `new` themselves are left alone."""
	from janadhikara.app_modules import APP_MODULES

	doctypes = frappe.get_all("DocType", filters={"module": ["in", APP_MODULES], "custom": 0, "istable": 0}, pluck="name")
	for parent in doctypes:
		if parent in (old, new):
			continue
		for df in frappe.get_meta(parent).fields:
			if df.fieldtype != "Link" or df.options != old:
				continue
			existing = frappe.db.get_value(
				"Property Setter", {"doc_type": parent, "field_name": df.fieldname, "property": "options"}, "name"
			)
			if existing:
				frappe.db.set_value("Property Setter", existing, "value", new)
			else:
				frappe.make_property_setter(
					{"doctype": parent, "fieldname": df.fieldname, "property": "options", "value": new, "property_type": "Text"},
					is_system_generated=False,
				)
			frappe.clear_cache(doctype=parent)


def _swap_sidebar(old, new, shown_as=None):
	"""The sidebar entry for `old` becomes one for `new` (same place, same icon). `shown_as` is the name users see
	and the address segment ("Settlement Profile" / settlement-profile): the city's short code stays out of both."""
	if not frappe.db.exists("DocType", "App Module Group"):
		return
	for name in frappe.get_all("App Module Group", pluck="name"):
		setting = frappe.get_doc("App Module Group", name)
		changed = False
		for row in setting.items or []:
			if row.item_type == "DocType" and row.doctype_name == old:
				row.doctype_name = new
				row.label = shown_as
				row.route = frappe.scrub(shown_as).replace("_", "-") if shown_as else None
				changed = True
		if changed:
			setting.flags.ignore_permissions = True
			setting.save()


def _drop_master_links(pack):
	"""Take the city's master data entries out of the sidebar's Master Data (when the site's city changes)."""
	prefix = pack.get("prefix")
	if not prefix or not frappe.db.exists("DocType", "App Module Group"):
		return
	for name in frappe.get_all("App Module Group", pluck="name"):
		setting = frappe.get_doc("App Module Group", name)
		keep = [row for row in setting.items or [] if not (row.doctype_name or "").startswith(f"{prefix} Municipal ")]
		if len(keep) != len(setting.items or []):
			setting.set("items", keep)
			setting.flags.ignore_permissions = True
			setting.save()
