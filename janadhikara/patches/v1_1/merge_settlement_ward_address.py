import frappe

# Ward and Address on the Details tab asked the same things as questionnaire
# Q3 (Ward No) and Q19.1 (Location details): keep the questionnaire fields,
# carry the saved values over and point the map-capture rule at them.
MERGE = {"ward": "q3_ward_no_city_corporation", "address": "q19_1_location_details_settlement"}


def execute():
	for old, new in MERGE.items():
		if frappe.db.has_column("Settlement", old) and frappe.db.has_column("Settlement", new):
			frappe.db.sql(
				f"update `tabSettlement` set `{new}` = `{old}` where ifnull(`{new}`, '') = '' and ifnull(`{old}`, '') != ''"
			)
		frappe.db.sql(
			"""update `tabField Function Mapping Item` i
			join `tabField Function Mapping` m on m.name = i.parent
			set i.target_field = %s
			where m.target_doctype = 'Settlement' and i.target_field = %s""",
			(new, old),
		)
	frappe.db.commit()
