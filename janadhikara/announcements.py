"""Announcements also reach people as notifications (the bell, push alerts):
the moment one is published, and - for one scheduled to start later - on its start date."""

import frappe
from frappe.utils import getdate, nowdate

MAX_RECIPIENTS = 2000


def _audience_users(doc):
	"""Enabled users the announcement is meant for."""
	if doc.audience == "Specific Users":
		users = [row.user for row in doc.users or []]
	elif doc.audience == "Specific Roles":
		roles = [row.role for row in doc.roles or []]
		users = frappe.get_all("Has Role", filters={"role": ["in", roles], "parenttype": "User"}, pluck="parent") if roles else []
	else:
		users = frappe.get_all("User", filters={"user_type": "System User"}, pluck="name", limit_page_length=MAX_RECIPIENTS)
	if not users:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", list(set(users))], "enabled": 1, "user_type": "System User"},
		fields=["name", "email"],
		limit_page_length=MAX_RECIPIENTS,
	)


def _already_notified(name):
	return bool(frappe.db.exists("Notification Log", {"document_type": "Announcement", "document_name": name}))


def notify(doc):
	"""Create one notification per recipient (bell + push). Safe to call twice."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	if _already_notified(doc.name):
		return
	recipients = [u.email or u.name for u in _audience_users(doc) if u.name not in ("Administrator", "Guest")]
	if not recipients:
		return
	message = frappe.utils.strip_html(doc.message or "").strip()
	subject = f"<strong>{frappe.utils.escape_html(doc.title)}</strong>"
	if message:
		subject += f": {frappe.utils.escape_html(message[:140])}"
	enqueue_create_notification(
		recipients,
		{
			"type": "Alert",
			"document_type": "Announcement",
			"document_name": doc.name,
			"subject": subject,
			"from_user": frappe.session.user,
			"link": frappe.utils.get_url("/janadhikara/home"),
		},
	)


def _live_today(doc):
	if not doc.enabled:
		return False
	start = getdate(doc.start_date) if doc.start_date else None
	end = getdate(doc.end_date) if doc.end_date else None
	today = getdate(nowdate())
	return (not start or start <= today) and (not end or end >= today)


def announcement_saved(doc, method=None):
	"""Announcement on_update: tell people when it goes live (new, or switched on)."""
	before = doc.get_doc_before_save()
	just_enabled = doc.enabled and (not before or not before.enabled)
	if just_enabled and _live_today(doc):
		notify(doc)


def notify_started_announcements():
	"""Scheduler (daily): announcements whose start date has arrived."""
	for name in frappe.get_all("Announcement", filters={"enabled": 1}, pluck="name"):
		doc = frappe.get_doc("Announcement", name)
		if _live_today(doc):
			try:
				notify(doc)
			except Exception:
				frappe.log_error(title=f"Announcement notification failed: {name}")
