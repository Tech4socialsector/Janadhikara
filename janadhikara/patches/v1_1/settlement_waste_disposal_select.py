import frappe

OPTIONS = ("Government-designated space", "Unregulated space")


def execute():
	"""Q18.4.2 Where do they dispose waste? is now a choice between two options instead of free text: clear the
	old written answers, which no longer fit and would stop the record from being saved."""
	frappe.db.sql(
		"update `tabSettlement` set q18_4_2_where_they_dispose_waste = null where q18_4_2_where_they_dispose_waste not in %s",
		(OPTIONS,),
	)
