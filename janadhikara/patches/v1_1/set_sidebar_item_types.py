import frappe


def execute():
	"""Sidebar items gained a Type (Link / Section Break / Spacer). Every item
	that existed before is a Link."""
	frappe.reload_doc("app_config", "doctype", "app_module_doctype_item", force=True)
	frappe.db.sql(
		"update `tabApp Module DocType Item` set item_type = 'Link' where ifnull(item_type, '') = ''"
	)
	frappe.cache().delete_value("janadhikara-modules")
	frappe.db.commit()
