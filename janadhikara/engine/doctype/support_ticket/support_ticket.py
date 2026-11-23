# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from janadhikara.helpdesk import AGENT_ROLE, CLOSED, MANAGER_ROLE, _city, _sla_due, is_agent, _notify, team_users


class SupportTicket(Document):
	def validate(self):
		if self.is_new():
			self.raised_by = frappe.session.user
			self.city = _city()
			self.status = "Open"
			self.sla_due = _sla_due(self.priority)
		else:
			before = self.get_doc_before_save()
			if not is_agent():
				self.restrict_requester(before)
			elif before and before.priority != self.priority:
				self.sla_due = _sla_due(self.priority, self.creation)
		if self.assigned_to and not is_agent(self.assigned_to):
			frappe.throw(_("{0} is not on the help desk team (role {1} or {2}).").format(self.assigned_to, AGENT_ROLE, MANAGER_ROLE))
		if self.status in CLOSED and not self.resolved_on:
			self.resolved_on = now_datetime()
		elif self.status not in CLOSED:
			self.resolved_on = None

	def restrict_requester(self, before):
		"""A requester can reword their own ticket and close or reopen it; everything else is the team's."""
		for field in ("priority", "assigned_to", "resolution", "ticket_type", "sla_due", "first_response_on", "raised_by"):
			if before and self.get(field) != before.get(field):
				frappe.throw(_("Only the help desk team can change {0}.").format(self.meta.get_label(field)), frappe.PermissionError)

	def after_insert(self):
		_notify(team_users(), self, _("New {0} ticket {1}: {2}").format(_(self.ticket_type), self.name, self.subject), self.raised_by)
