"""Pages of the app that are switched on or off per role through an App Module Setting, like any other module."""
import frappe

# module name -> the module's settings. Created once if missing; after that its roles, label and icon are changed in
# App Module Setting (and a migrate leaves them alone: this module is not exported as a fixture).
SYNC_MODULE = {
	"module_name": "Sync Data",
	"label": "Sync Data",
	"icon": "cloud-upload",
	"sort_order": 9,
	"enabled": 1,
	"restrict_by_role": 1,
	"roles": ["ORW", "Program Coordinator", "Program Manager", "Organization Admin"],
	"items": [{"item_type": "Page", "label": "Sync Data", "route": "sync-data", "icon": "cloud-upload"}],
}


def ensure_sync_module():
	"""Offline sync is a module: whoever's role is on it sees Sync Data (home tile, sidebar, phone menu)."""
	cfg = SYNC_MODULE
	if frappe.db.exists("App Module Setting", cfg["module_name"]):
		return
	frappe.get_doc(
		{
			"doctype": "App Module Setting",
			"module_name": cfg["module_name"],
			"label": cfg["label"],
			"icon": cfg["icon"],
			"sort_order": cfg["sort_order"],
			"enabled": cfg["enabled"],
			"restrict_by_role": cfg["restrict_by_role"],
			"roles": [{"role": r} for r in cfg["roles"] if frappe.db.exists("Role", r)],
			"doctypes": cfg["items"],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
