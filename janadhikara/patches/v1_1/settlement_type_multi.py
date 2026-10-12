import frappe

OLD_TO_NEW = {
	"Category A": "Category A – Settlements with one room pucca houses or tin/bamboo houses with basic amenities",
	"Category B": "Category B – Settlements with pucca, semi pucca or tin/bamboo/stilt houses mainly on railway land/army land or other government land with basic amenities",
	"Category C": "Category C – Settlements in private land - rented gated compounds with small rooms primarily made of tin/bamboo with pucca houses only in some pockets. Shared toilets and basic amenities provided by the owners",
	"Category D": "Category D – Settlements near railway or dumping ground in make-shift houses with no amenities"
}


def execute():
	"""Q6 Type of Settlement is now pick-several, with the description inside each option: carry the saved
	single values over, and drop the old Q6 translations (the new ones are imported on migrate)."""
	for old, new in OLD_TO_NEW.items():
		frappe.db.sql("update `tabSettlement` set q6_type_settlement = %s where q6_type_settlement = %s", (new, old))
	frappe.db.delete("Translation", {"context": ["like", "janadhikara:field:Settlement:q6_type_settlement:%"]})
