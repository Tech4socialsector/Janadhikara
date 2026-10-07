import frappe

# Household Profile now follows the household questionnaire sheet:
# - the cooking-fuel master holds the five fuels of the sheet (LPG is the sheet's "Gas"),
# - AI policy rules for fields that no longer exist are dropped.
FUELS = ("Firewood", "Charcoal", "Kerosene", "Electricity", "Gas")


def execute():
	if frappe.db.exists("Cooking Fuel", "LPG") and not frappe.db.exists("Cooking Fuel", "Gas"):
		frappe.rename_doc("Cooking Fuel", "LPG", "Gas", force=True)
	for fuel in FUELS:
		if not frappe.db.exists("Cooking Fuel", fuel):
			frappe.get_doc({"doctype": "Cooking Fuel", "fuel_name": fuel}).insert(ignore_permissions=True)
	for fuel in frappe.get_all("Cooking Fuel", pluck="name"):
		if fuel not in FUELS and not frappe.db.exists("Household Cooking Fuel", {"fuel": fuel}):
			frappe.delete_doc("Cooking Fuel", fuel, force=1, ignore_permissions=True)

	for policy in frappe.get_all("AI Data Policy", pluck="name"):
		doc = frappe.get_doc("AI Data Policy", policy)
		if not frappe.db.exists("DocType", doc.target_doctype):
			continue
		fields = {df.fieldname for df in frappe.get_meta(doc.target_doctype).fields}
		kept = [row for row in doc.field_rules if row.policy_field in fields]
		if len(kept) != len(doc.field_rules):
			doc.field_rules = kept
			doc.save(ignore_permissions=True)
	frappe.db.commit()
