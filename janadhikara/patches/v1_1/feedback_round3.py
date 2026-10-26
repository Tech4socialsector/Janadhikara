import frappe

from janadhikara.baseline.doctype.household_profile.household_profile import count_households, household_label


def execute():
	"""Partner feedback: households are picked by HHID, head and house; each settlement shows how many households were
	profiled; the household map is gone (the settlement keeps the location)."""
	for row in frappe.get_all("Household Profile", fields=["name", "hhid", "household_head_name", "house_no", "street_name"]):
		frappe.db.set_value("Household Profile", row.name, "household_label", household_label(row), update_modified=False)
	for settlement in frappe.get_all("Settlement", pluck="name"):
		count_households(settlement)
	# removed directly: the rule can't be loaded any more now that its map field is gone
	for doctype, key in (("Field Function Mapping", "name"), ("Field Function Mapping Item", "parent")):
		if frappe.db.table_exists(doctype):
			frappe.db.delete(doctype, {key: "Household map capture"})
