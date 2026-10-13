import frappe


def execute():
	"""Cluster is a master list (Cluster doctype) and Settlement.cluster links to it. Make a Cluster for every name already
	typed on a Settlement, and fill the cluster on the households and individuals from their settlement."""
	names = frappe.db.sql("select distinct cluster from `tabSettlement` where ifnull(cluster, '') != ''", pluck=True)
	for name in names:
		if not frappe.db.exists("Cluster", name):
			frappe.get_doc({"doctype": "Cluster", "cluster_name": name, "enabled": 1}).insert(ignore_permissions=True)
	if frappe.db.has_column("Household Profile", "cluster"):
		frappe.db.sql(
			"""update `tabHousehold Profile` h join `tabSettlement` s on s.name = h.settlement
			set h.cluster = s.cluster where ifnull(h.cluster, '') = ''"""
		)
	if frappe.db.has_column("Individual Profile", "cluster"):
		frappe.db.sql(
			"""update `tabIndividual Profile` i join `tabSettlement` s on s.name = i.settlement_intervention_unit
			set i.cluster = s.cluster where ifnull(i.cluster, '') = ''"""
		)
	frappe.db.commit()
