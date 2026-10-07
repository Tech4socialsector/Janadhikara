"""Worklist: ToDos the app raises by itself.

- A Household Profile marked "Revision Needed" gives its data collector a task;
  the task closes when the household moves on (Validated / Completed / back to
  work).
- A daily job nudges the data collector of a household that has sat in Draft /
  Partially Completed for STALE_DAYS without an update.

Everything goes through Frappe's own assignment (`assign_to`), so the tasks are
ordinary ToDos (reference = the household) and show up in the Worklist."""

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add, close_all_assignments
from frappe.utils import add_days, getdate, nowdate

STALE_DAYS = 7
OPEN_STATUSES = ("Partially Completed",)
DONE_STATUSES = ("Validated", "Completed")


def _title(doc):
	return doc.get("respondent_name") or doc.name


def _has_open_task(doctype, name, user):
	return frappe.db.exists(
		"ToDo",
		{"reference_type": doctype, "reference_name": name, "allocated_to": user, "status": "Open"},
	)


def _worker_user(employee):
	"""The login of a worker (Employee row): its User link, or its email."""
	if not employee:
		return None
	user, email = frappe.db.get_value("Employee", employee, ["user", "email"]) or (None, None)
	return user or (email if email and frappe.db.exists("User", email) else None)


def _assign(doc, description, priority="Medium", due_in_days=3):
	user = _worker_user(doc.get("assigned_worker"))
	if not user or not frappe.db.get_value("User", user, "enabled"):
		return
	if _has_open_task(doc.doctype, doc.name, user):
		return
	_add(
		{
			"doctype": doc.doctype,
			"name": doc.name,
			"assign_to": [user],
			"description": description,
			"priority": priority,
			"date": add_days(nowdate(), due_in_days),
		},
		ignore_permissions=True,
	)


def household_updated(doc, method=None):
	"""Household Profile on_update."""
	if doc.get("validation_status") == "Revision Needed":
		before = doc.get_doc_before_save()
		if before and before.get("validation_status") == "Revision Needed" and not doc.is_new():
			return  # already has its revision task: unrelated saves don't re-assign
		note = f" - {doc.validation_comments}" if doc.get("validation_comments") else ""
		_assign(
			doc,
			_("Revise household {0}{1}").format(_title(doc), note),
			priority="High",
			due_in_days=2,
		)
		return

	before = doc.get_doc_before_save()
	if (before and before.get("validation_status") == "Revision Needed") or doc.get("validation_status") == "Validated" or doc.status in DONE_STATUSES:
		# Frappe tells the assignee itself when an assignment is closed - don't say it twice.
		frappe.flags.janadhikara_system_close = True
		try:
			close_all_assignments(doc.doctype, doc.name, ignore_permissions=True)
		finally:
			frappe.flags.janadhikara_system_close = False


def nudge_stale_households():
	"""Scheduler (daily): Draft / Partially Completed households with no update for STALE_DAYS."""
	cutoff = add_days(nowdate(), -STALE_DAYS)
	households = frappe.get_all(
		"Household Profile",
		filters={"status": ["in", OPEN_STATUSES], "modified": ["<", cutoff]},
		fields=["name", "respondent_name", "assigned_worker", "status"],
		order_by="modified asc",
		limit=500,
	)
	for row in households:
		try:
			doc = frappe._dict(row, doctype="Household Profile")
			_assign(
				doc,
				_("Household {0} has had no update for {1} days - please continue or close it").format(
					_title(doc), STALE_DAYS
				),
				priority="Medium",
				due_in_days=3,
			)
		except Exception:
			frappe.log_error(title=f"Worklist nudge failed for {row.name}")
	frappe.db.commit()


def notify_new_task(doc, method=None):
	"""ToDo after_insert: tell the person a task was just given to them.

	Tasks created through Frappe's assignment (a reference record - the ones this
	module raises) already notify via `assign_to`; this covers a plain task made
	in the Worklist. The Notification Log it creates is pushed live to the user's
	open app (realtime) and emailed if they have Assignment emails on."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	if doc.reference_type and doc.reference_name:
		return
	giver = doc.assigned_by or doc.owner
	if not doc.allocated_to or not frappe.db.get_value("User", doc.allocated_to, "enabled"):
		return

	task = (doc.get("task_title") or frappe.utils.strip_html(doc.description or "") or _("a new task")).strip()
	if doc.allocated_to == giver:
		# A task you add for yourself: Frappe never notifies a user about their own
		# action, so it goes out with no sender - it still pops up, emails and pushes.
		log = {"type": "Assignment", "subject": _("Added to your worklist: {0}").format(frappe.bold(task[:140]))}
	else:
		giver_name = frappe.db.get_value("User", giver, "full_name") or giver
		log = {
			"type": "Assignment",
			"subject": _("{0} gave you a task: {1}").format(frappe.bold(giver_name), task[:140]),
			"from_user": giver,
		}
	# Frappe matches recipients by email address (Administrator's differs from its name).
	recipient = frappe.db.get_value("User", doc.allocated_to, "email") or doc.allocated_to
	enqueue_create_notification(
		[recipient],
		{
			**log,
			"document_type": "ToDo",
			"document_name": doc.name,
			"email_content": doc.description,
			"link": frappe.utils.get_url(f"/janadhikara/todo/{doc.name}"),
		},
	)


def ensure_task_title(doc, method=None):
	"""ToDo before_validate: a task always has a title - cut from the description
	when none was given (the tasks this app raises, or one made in the desk)."""
	if doc.get("task_title"):
		return
	text = frappe.utils.strip_html(doc.get("description") or "").strip()
	if text:
		doc.task_title = (text.splitlines()[0] if text else text)[:140]


# --- Team worklists ---------------------------------------------------------
# A partner admin / supervisor can look at the worklists of the people they
# oversee (read-only); programme-level roles see every partner's workers.
PROGRAMME_ROLES = {"System Manager", "Program Coordinator", "Program Manager"}


@frappe.whitelist()
def get_team_members():
	"""[{ user, full_name, role, partner }] whose worklist the signed-in user may view."""
	from janadhikara.api import get_user_employee

	roles = set(frappe.get_roles())
	me = frappe.session.user
	filters = {"parenttype": "Partner Details", "status": "Active"}
	allowed_roles = None  # None = any role

	if roles & PROGRAMME_ROLES:
		pass
	else:
		employee = get_user_employee()
		if not employee:
			return []
		if "Organization Admin" in roles:
			filters["parent"] = employee.parent
		elif "Supervisor" in roles:
			filters["parent"] = employee.parent
			allowed_roles = ["Data Collector"]
		else:
			return []

	if allowed_roles:
		filters["role"] = ["in", allowed_roles]

	rows = frappe.get_all(
		"Employee",
		filters=filters,
		fields=["user", "email", "worker_name", "role", "parent"],
		order_by="worker_name asc",
		limit_page_length=500,
	)
	members, seen = [], set()
	for row in rows:
		user = row.user or row.email
		if not user or user == me or user in seen or not frappe.db.exists("User", {"name": user, "enabled": 1}):
			continue
		seen.add(user)
		members.append({"user": user, "full_name": row.worker_name or user, "role": row.role, "partner": row.parent})
	return members


@frappe.whitelist()
def get_team_tasks(user):
	"""The ToDos allocated to `user`, if the signed-in user may view that person's worklist."""
	if user != frappe.session.user and user not in {m["user"] for m in get_team_members()}:
		frappe.throw(_("You can't view this person's worklist."), frappe.PermissionError)
	return frappe.get_all(
		"ToDo",
		filters={"allocated_to": user},
		fields=[
			"name", "task_title", "description", "status", "date", "task_time", "creation", "priority", "reference_type", "reference_name",
			"allocated_to", "assigned_by", "assigned_by_full_name", "modified",
		],
		order_by="modified desc",
		limit_page_length=300,
	)


# --- A notification for every change to a task ---------------------------------
def _task_title(doc):
	return (doc.get("task_title") or frappe.utils.strip_html(doc.get("description") or "") or _("a task")).strip()[:140]


def _email(user):
	return frappe.db.get_value("User", user, "email") or user


def _notify_task(todo, users, subject, from_user=None, reference=True):
	"""One Notification Log (-> bell, email, push) per user."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	for user in users:
		if not user or not frappe.db.get_value("User", user, "enabled"):
			continue
		enqueue_create_notification(
			[_email(user)],
			{
				"type": "Assignment",
				# Frappe removes a document's notifications when it is deleted, so the
				# "deleted" one must not point at the task.
				"document_type": "ToDo" if reference else None,
				"document_name": todo.name if reference else None,
				"subject": subject,
				# Frappe never notifies a user about their own action; for a task kept
				# by one person we leave the sender off so they still get the alert.
				"from_user": from_user if from_user and from_user != user else None,
				"email_content": todo.get("description"),
				"link": frappe.utils.get_url(f"/janadhikara/todo/{todo.name}") if reference else frappe.utils.get_url("/janadhikara/worklist"),
			},
		)


def todo_changed(doc, method=None):
	"""ToDo on_update: tell the other person (or the owner, for a task of their own) what changed."""
	if frappe.flags.janadhikara_system_close:
		return
	before = doc.get_doc_before_save()
	if not before:
		return  # a new task is announced by notify_new_task

	actor = frappe.session.user
	actor_name = frappe.bold(frappe.db.get_value("User", actor, "full_name") or actor)
	title = frappe.bold(_task_title(doc))

	changes = []
	if before.status != doc.status:
		changes.append(
			{
				"Closed": _("marked it as done"),
				"Open": _("reopened it"),
				"Cancelled": _("cancelled it"),
			}.get(doc.status, _("set it to {0}").format(doc.status))
		)
	if (before.date != doc.date) or (str(before.get("task_time") or "") != str(doc.get("task_time") or "")):
		when = " ".join(filter(None, [str(doc.date or ""), str(doc.get("task_time") or "")[:5]])) or _("no date")
		changes.append(_("rescheduled it to {0}").format(when))
	if before.priority != doc.priority:
		changes.append(_("changed its priority to {0}").format(doc.priority))
	if (before.get("task_title") != doc.get("task_title")) or (before.description != doc.description):
		changes.append(_("edited it"))

	# Reassigned: the new person is told, the previous one hears it moved on.
	if before.allocated_to != doc.allocated_to:
		_notify_task(
			doc, [doc.allocated_to], _("{0} assigned you a task: {1}").format(actor_name, title), actor
		)
		if before.allocated_to:
			new_name = frappe.db.get_value("User", doc.allocated_to, "full_name") or doc.allocated_to
			_notify_task(
				doc,
				[before.allocated_to],
				_("{0} reassigned {1} to {2}").format(actor_name, title, frappe.bold(new_name)),
				actor,
			)

	if not changes:
		return
	parties = {doc.allocated_to, doc.assigned_by or doc.owner} - {actor}
	if before.allocated_to != doc.allocated_to:
		parties.discard(doc.allocated_to)  # already told above
	if not parties and before.allocated_to == doc.allocated_to:
		parties = {actor}  # a task of their own
	_notify_task(doc, parties, _("{0} {1}: {2}").format(actor_name, "; ".join(changes), title), actor)


def todo_deleted(doc, method=None):
	"""ToDo on_trash: tell the other person a task was removed."""
	if frappe.flags.janadhikara_system_close:
		return
	actor = frappe.session.user
	actor_name = frappe.bold(frappe.db.get_value("User", actor, "full_name") or actor)
	parties = {doc.allocated_to, doc.assigned_by or doc.owner} - {actor}
	if not parties:
		parties = {actor}
	_notify_task(
		doc, parties, _("{0} deleted the task: {1}").format(actor_name, frappe.bold(_task_title(doc))), actor, reference=False
	)
