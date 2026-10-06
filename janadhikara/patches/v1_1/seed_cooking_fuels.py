import frappe

FUELS = ["LPG", "Firewood", "Kerosene", "Electricity / Induction", "Biogas", "Cow-dung cakes", "Charcoal", "Other"]


def execute():
	"""Starter list for the household's "Fuels used for cooking". Admins can add or rename
	fuels from Master Data > Cooking Fuel; only missing ones are added here."""
	for name in FUELS:
		if not frappe.db.exists("Cooking Fuel", name):
			frappe.get_doc({"doctype": "Cooking Fuel", "fuel_name": name, "enabled": 1}).insert(ignore_permissions=True)
	frappe.db.commit()
