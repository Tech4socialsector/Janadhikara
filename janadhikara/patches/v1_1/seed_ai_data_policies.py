import frappe

from janadhikara.ai.policy import ensure_policies, seed_policies


def execute():
	"""Give the assistant access only to what's been reviewed: the doctypes in
	ai/policy.py's SEED (with their confidential fields hidden), and a
	disabled policy for every other doctype of the app."""
	seed_policies()
	ensure_policies()
	frappe.db.commit()
