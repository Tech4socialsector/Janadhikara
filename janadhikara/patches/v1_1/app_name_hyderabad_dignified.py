import frappe

NEW_NAME = "Hyderabad Dignified"


def execute():
	"""The app is now called Hyderabad Dignified. A name an administrator already changed in App Setting is kept."""
	if frappe.db.get_single_value("App Setting", "app_name") in (None, "", "Janadhikara"):
		frappe.db.set_single_value("App Setting", "app_name", NEW_NAME)
	if frappe.db.get_single_value("Website Settings", "app_name") in (None, "", "Janadhikara"):
		frappe.db.set_single_value("Website Settings", "app_name", NEW_NAME)
