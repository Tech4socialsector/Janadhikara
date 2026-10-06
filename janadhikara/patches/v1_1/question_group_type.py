import frappe


def execute():
	"""Questions that already belong to a section keep it: they become "Section" questions (the
	new "Group as" field would otherwise default to an individual question and drop the section)."""
	frappe.reload_doc("masters", "doctype", "question_bank")
	frappe.db.sql(
		"""update `tabQuestion Bank` set group_type = 'Section'
		where ifnull(section_group, '') != '' and ifnull(group_type, '') in ('', 'Individual question')"""
	)
	frappe.db.sql(
		"""update `tabQuestion Bank` set group_type = 'Individual question' where ifnull(group_type, '') = ''"""
	)
