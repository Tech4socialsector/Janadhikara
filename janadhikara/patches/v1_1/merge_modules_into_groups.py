import frappe

from janadhikara.menu import OLD_MODULE_GROUP, PAGES, ensure_module_groups

OLD = ("App Module Setting", "App Module DocType Item")
ROUTE_PAGE = {route: name for name, (route, _icon) in PAGES.items()}


def execute():
	"""App Module Setting and its DocType Item table are replaced by App Module Group and its items: each module's
	items move into its group (its Module Group, else Administration for Engine/Masters, Programme Management for Sync
	Data, Data Collection for the rest); a module's "Show Sidebar" and its roles carry over to the group / its items.
	The old doctypes are then deleted."""
	if not frappe.db.table_exists("App Module Setting"):
		return
	ensure_module_groups()
	# read with queries: the old doctypes' Python classes are gone with them
	for module in frappe.get_all("App Module Setting", fields=["name", "module_group", "use_sidebar", "restrict_by_role"], order_by="sort_order asc"):
		name = module.name
		target = module.module_group or OLD_MODULE_GROUP.get(name) or "Data Collection"
		if not frappe.db.exists("App Module Group", target):
			target = "Data Collection"
		group = frappe.get_doc("App Module Group", target)
		if module.use_sidebar:
			group.use_sidebar = 1
		role_rows = frappe.get_all("Has Role", filters={"parent": name, "parenttype": "App Module Setting", "parentfield": "roles"}, pluck="role", order_by="idx")
		roles = "\n".join(role_rows) if module.restrict_by_role and role_rows else None
		rows = frappe.get_all("App Module DocType Item", filters={"parent": name}, fields=["item_type", "doctype_name", "label", "icon", "route", "child"], order_by="idx")
		have = {(r.item_type, r.doctype_name or r.page) for r in group.items or []}
		for row in rows:
			kind = row.item_type or "Link"
			if kind == "Link":
				if not row.doctype_name or ("DocType", row.doctype_name) in have:
					continue
				group.append("items", {"item_type": "DocType", "doctype_name": row.doctype_name, "label": row.label, "icon": row.icon, "route": row.route, "child": row.child, "roles": roles})
				have.add(("DocType", row.doctype_name))
			elif kind == "Page":
				page = ROUTE_PAGE.get(row.route)
				if not page:
					continue
				found = [r for r in group.items or [] if r.item_type == "Page" and r.page == page]
				if found:
					if roles:
						found[0].roles = roles  # the roles this site had set on the module
				else:
					group.append("items", {"item_type": "Page", "page": page, "label": row.label, "icon": row.icon, "roles": roles})
			elif kind in ("Section Break", "Spacer"):
				group.append("items", {"item_type": kind, "label": row.label, "icon": row.icon})
		group.flags.ignore_permissions = True
		group.save()
	for old in OLD:
		if frappe.db.exists("DocType", old):
			frappe.delete_doc("DocType", old, force=True, ignore_permissions=True)
		frappe.db.sql_ddl(f"drop table if exists `tab{old}`")
	frappe.db.commit()
