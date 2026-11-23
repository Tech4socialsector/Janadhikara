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
	# read with queries: the old doctypes' Python classes are gone with them. A site that never ran the releases which
	# added some of these columns (Module Group, Show Sidebar, ...) simply does not have them: read what exists.
	cols = set(frappe.db.get_table_columns("App Module Setting"))
	want = ["module_group", "use_sidebar", "restrict_by_role", "sort_order"]
	for module in frappe.get_all("App Module Setting", fields=["name"] + [c for c in want if c in cols], order_by="sort_order asc" if "sort_order" in cols else "creation asc"):
		name = module.name
		target = module.get("module_group") or OLD_MODULE_GROUP.get(name) or "Data Collection"
		if not frappe.db.exists("App Module Group", target):
			target = "Data Collection"
		group = frappe.get_doc("App Module Group", target)
		if module.get("use_sidebar"):
			group.use_sidebar = 1
		role_rows = frappe.get_all("Has Role", filters={"parent": name, "parenttype": "App Module Setting", "parentfield": "roles"}, pluck="role", order_by="idx")
		roles = "\n".join(role_rows) if module.get("restrict_by_role") and role_rows else None
		item_cols = set(frappe.db.get_table_columns("App Module DocType Item"))
		rows = frappe.get_all("App Module DocType Item", filters={"parent": name}, fields=[c for c in ("item_type", "doctype_name", "label", "icon", "route", "child") if c in item_cols], order_by="idx")
		have = {(r.item_type, r.doctype_name or r.page) for r in group.items or []}
		for row in rows:
			kind = row.get("item_type") or "Link"
			if kind == "Link":
				# a doctype this site no longer has (removed in an earlier release) cannot be listed
				if not row.get("doctype_name") or ("DocType", row.doctype_name) in have or not frappe.db.exists("DocType", row.doctype_name):
					continue
				group.append("items", {"item_type": "DocType", "doctype_name": row.doctype_name, "label": row.get("label"), "icon": row.get("icon"), "route": row.get("route"), "child": row.get("child"), "roles": roles})
				have.add(("DocType", row.doctype_name))
			elif kind == "Page":
				page = ROUTE_PAGE.get(row.get("route"))
				if not page:
					continue
				found = [r for r in group.items or [] if r.item_type == "Page" and r.page == page]
				if found:
					if roles:
						found[0].roles = roles  # the roles this site had set on the module
				else:
					group.append("items", {"item_type": "Page", "page": page, "label": row.get("label"), "icon": row.get("icon"), "roles": roles})
			elif kind in ("Section Break", "Spacer"):
				group.append("items", {"item_type": kind, "label": row.get("label"), "icon": row.get("icon")})
		group.flags.ignore_permissions = True
		group.save()
	for old in OLD:
		if frappe.db.exists("DocType", old):
			frappe.delete_doc("DocType", old, force=True, ignore_permissions=True)
		frappe.db.sql_ddl(f"drop table if exists `tab{old}`")
	frappe.db.commit()
