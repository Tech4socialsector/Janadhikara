"""My notification preferences (Settings > Notifications): the in-app bell, email
and push. Stored in Frappe's own Notification Settings, so Frappe's email and bell
logic honours them with no extra plumbing. Push is per device (Push Subscription)."""

import frappe
from frappe.desk.doctype.notification_settings.notification_settings import create_notification_settings

EMAIL_TYPE = "Assignment"


def _settings(user):
	create_notification_settings(user)
	return frappe.get_doc("Notification Settings", user)


@frappe.whitelist()
def get_notification_preferences():
	user = frappe.session.user
	settings = _settings(user)
	email_types = {row.notification_type for row in settings.email_notification_types}
	return {
		"in_app": bool(settings.enabled),
		"email": bool(settings.enable_email_notifications and EMAIL_TYPE in email_types),
		"push_devices": frappe.db.count("Push Subscription", {"user": user}),
	}


@frappe.whitelist(methods=["POST"])
def set_notification_preferences(in_app=None, email=None):
	"""Any of the two may be passed; the other is left alone."""
	settings = _settings(frappe.session.user)
	if in_app is not None:
		settings.enabled = 1 if frappe.parse_json(in_app) else 0
	if email is not None:
		wanted = bool(frappe.parse_json(email))
		settings.enable_email_notifications = 1 if wanted else 0
		if wanted:
			settings.enable_email_assignment = 1
			if not any(row.notification_type == EMAIL_TYPE for row in settings.email_notification_types):
				settings.append("email_notification_types", {"notification_type": EMAIL_TYPE})
	settings.flags.ignore_permissions = True
	settings.save()
	return get_notification_preferences()


@frappe.whitelist()
def get_my_notifications(limit: int = 20):
	"""The signed-in user's own notifications. (Frappe's own list returns every user's
	logs to the Administrator account, so its "Mark all read" never cleared them.)"""
	logs = frappe.get_all(
		"Notification Log",
		filters={"for_user": frappe.session.user},
		fields=["name", "subject", "type", "read", "creation", "document_type", "document_name", "link", "from_user", "for_user", "email_content"],
		order_by="creation desc",
		limit_page_length=max(1, min(int(limit), 100)),
	)
	user_info = frappe._dict()
	for user in {log.from_user for log in logs if log.from_user}:
		frappe.utils.add_user_info(user, user_info)
	return {"notification_logs": logs, "user_info": user_info}
