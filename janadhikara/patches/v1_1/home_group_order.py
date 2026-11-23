import frappe

from janadhikara.menu import ADMIN, DATA, LEGACY, PROGRAMME

ORDER = [ADMIN, PROGRAMME, DATA, "Help & Support"]


def execute():
	"""The standard Home groups are now Administration, Dashboard & Reports, Base Line, Help & Support, in that order.
	A site that still has the earlier names (Programme Management, Data Collection) gets the new ones; a name already
	changed by the site's admins is left alone."""
	if not frappe.db.table_exists("App Module Group"):
		return
	for new, olds in LEGACY.items():
		for old in olds:
			if frappe.db.exists("App Module Group", old) and not frappe.db.exists("App Module Group", new):
				frappe.rename_doc("App Module Group", old, new, force=True)
	for order, name in enumerate(ORDER, start=1):
		if frappe.db.exists("App Module Group", name):
			frappe.db.set_value("App Module Group", name, "sort_order", order, update_modified=False)
	frappe.db.commit()
