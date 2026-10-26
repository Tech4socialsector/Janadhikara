import frappe

CONTEXTS = (
	"Settlement:boundary_area:%",
	"Settlement:boundary_perimeter:%",
	"Household Profile:cooking_fuels:%",
	"Household Profile:drinking_water_source:description",
	"Individual Profile:udid_applied:label",
	"Individual Profile:udid_number:label",
	"Individual Profile:respondent_name:description",
)


def execute():
	"""APF feedback: Q39 Fuels used for cooking is now a pick-several question kept on the household itself (it was a
	table of rows): carry the chosen fuels over. Old translations of the changed questions are dropped (the new ones
	are imported on migrate)."""
	if frappe.db.table_exists("Household Cooking Fuel"):
		chosen = {}
		for row in frappe.get_all(
			"Household Cooking Fuel", filters={"parenttype": "Household Profile", "parentfield": "cooking_fuels"}, fields=["parent", "fuel"], order_by="idx"
		):
			chosen.setdefault(row.parent, []).append(row.fuel)
		for household, fuels in chosen.items():
			if not frappe.db.get_value("Household Profile", household, "cooking_fuels"):
				frappe.db.set_value("Household Profile", household, "cooking_fuels", "\n".join(dict.fromkeys(fuels)), update_modified=False)
	for context in CONTEXTS:
		frappe.db.delete("Translation", {"context": ["like", "janadhikara:field:" + context]})
