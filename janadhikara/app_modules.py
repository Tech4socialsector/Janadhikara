"""The Frappe modules (folders under janadhikara/) whose doctypes belong to this app.

Shared doctypes live in Masters, App Config and Engine. The original programme's doctypes (Settlement, Household
Profile, Individual Profile and their child tables) live in Guwahati; they are used on every site, because other
cities still share the household and individual forms. A city with doctypes of its own gets a module named after it
(janadhikara/hyderabad/doctype/...), listed in CITY_MODULES and used only on that city's site."""

SHARED_MODULES = ("Masters", "App Config", "Engine", "Guwahati")
CITY_MODULES = ("Hyderabad",)
APP_MODULES = SHARED_MODULES + CITY_MODULES


def active_modules():
	"""The modules whose doctypes this site uses: the shared ones and its own city's (other cities' doctypes
	exist in the code but are not used here)."""
	from janadhikara.city_pack import city_module

	return SHARED_MODULES + ((city_module(),) if city_module() else ())


def refresh_module_map():
	"""before_migrate: Frappe reads the module list (modules.txt) once when the process starts, so a module added in
	this release - a new city's - would be skipped by the migrate that should create it. Read it again first."""
	import frappe

	frappe.cache.delete_value("app_modules")
	frappe.setup_module_map()
