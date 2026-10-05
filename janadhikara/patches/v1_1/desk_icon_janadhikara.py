import frappe


def execute():
	"""Desk home screen: show a Janadhikara app icon (opens the app at
	/janadhikara) and drop the old CHW App icon."""
	for name in frappe.get_all("Desktop Icon", filters={"label": ["like", "%CHW%"]}, pluck="name"):
		frappe.delete_doc("Desktop Icon", name, force=True, ignore_permissions=True)

	if not frappe.db.exists("Desktop Icon", "Janadhikara"):
		frappe.get_doc(
			{
				"doctype": "Desktop Icon",
				"label": "Janadhikara",
				"icon_type": "App",
				"app": "janadhikara",
				"link_type": "External",
				"link": "/janadhikara",
				"logo_url": "/assets/janadhikara/default-logo.png",
				"standard": 1,
				"hidden": 0,
			}
		).insert(ignore_permissions=True)
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.db.commit()
