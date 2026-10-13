import frappe

from janadhikara.statuses import ensure_statuses


def execute():
	"""Settlement has the same Status question as the two profiles. Settlements that exist take Completed when their
	profiling status (20.6) says so, otherwise Partially Completed."""
	ensure_statuses()
	if not frappe.db.has_column("Settlement", "validation_status"):
		return
	frappe.db.sql(
		"""update `tabSettlement` set validation_status =
		if(q20_6_profiling_status = 'Completed', 'Completed', 'Partially Completed')
		where ifnull(validation_status, '') = ''"""
	)
	frappe.db.commit()
