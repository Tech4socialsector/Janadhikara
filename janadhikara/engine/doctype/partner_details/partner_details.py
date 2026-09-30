# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# The 5 roles this app hands out via an Employee row's own Role field -
# the only roles ensure_employee_user is ever allowed to grant or revoke.
# Kept as an explicit list (not "whatever Employee.role's Select options
# currently are") so this stays correct even if that options string is
# ever edited later - and, more importantly, so this never touches a role
# unrelated to this app that a User might separately hold (System
# Manager, a desk-only role, ...): only these 5 are ever added or removed.
EMPLOYEE_MANAGED_ROLES = {
	"Data Collector",
	"Supervisor",
	"Program Manager",
	"Organization Admin",
	"Report Viewer",
}


class PartnerDetails(Document):
	def validate(self):
		for row in self.employees:
			self.ensure_employee_user(row)

	def ensure_employee_user(self, row):
		"""Make sure this Employee row's Email has a matching User account
		(creating one the first time this row is saved with an email that
		doesn't match an existing User), and that the account's own
		EMPLOYEE_MANAGED_ROLES membership exactly mirrors this row's
		current Role - the email is what identifies the account (Frappe's
		own convention: every User is keyed by email), so `user` itself is
		never picked by hand; it's just this row's own reflection of that
		lookup.
		"""
		if not row.email:
			return

		if not frappe.db.exists("User", row.email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": row.email,
					"first_name": row.worker_name or row.email,
					"send_welcome_email": 1,
					"user_type": "System User",
				}
			)
			if row.role:
				user.append("roles", {"role": row.role})
			user.insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", row.email)
			current_managed = {r.role for r in user.roles if r.role in EMPLOYEE_MANAGED_ROLES}
			desired_managed = {row.role} if row.role else set()
			if current_managed != desired_managed:
				# Only ever touch rows whose role is one of ours - drop
				# the ones we no longer want, keep everything else (any
				# non-Employee role) exactly as it was.
				user.roles = [r for r in user.roles if r.role not in EMPLOYEE_MANAGED_ROLES]
				if row.role:
					user.append("roles", {"role": row.role})
				user.save(ignore_permissions=True)

		row.user = row.email
