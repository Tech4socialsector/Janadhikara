"""The in-app help desk: tickets raised by the people using a city's site, worked by that site's help desk team.

Three kinds of user, by role:
- Requester: anyone signed in. Raises tickets and sees only their own, with the public replies.
- Agent (role "Help Desk Agent"): sees every ticket on the site, replies, writes internal notes, assigns, changes the status.
- Manager (role "Help Desk Manager"): everything an agent does, plus the overview (load, overdue, response times).
Every city has its own site, so its tickets stay on that site and carry the city's name."""

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime, strip_html
from frappe.utils.html_utils import clean_html

TICKET = "Support Ticket"
REPLY = "Support Ticket Reply"
AGENT_ROLE = "Help Desk Agent"
MANAGER_ROLE = "Help Desk Manager"
TYPES = ["Change Request", "New Implementation", "Bug / Issue", "Question"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
STATUSES = ["Open", "In Progress", "Waiting on Requester", "Resolved", "Closed"]
CLOSED = ("Resolved", "Closed")
SLA_HOURS = {"Urgent": 4, "High": 24, "Medium": 72, "Low": 168}
LIST_FIELDS = [
	"name", "subject", "ticket_type", "priority", "status", "raised_by", "raised_by_name", "assigned_to",
	"city", "creation", "modified", "sla_due",
]


def _tags(value):
	"""A record's _user_tags (",a,b") as a list."""
	return [t for t in (value or "").split(",") if t]


def _html(text):
	"""A message as safe HTML: rich text is cleaned, plain text (older messages, the request itself) is escaped with its line breaks."""
	text = text or ""
	if "<" in text and ">" in text:
		return clean_html(text)
	return frappe.utils.escape_html(text).replace("\n", "<br>")



# ---- who is who ---------------------------------------------------------------------------------------------------
def is_manager(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or MANAGER_ROLE in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)


def is_agent(user=None):
	user = user or frappe.session.user
	return is_manager(user) or AGENT_ROLE in frappe.get_roles(user)


def team_users():
	"""Enabled users who can work tickets (agents and managers)."""
	users = frappe.get_all("Has Role", filters={"role": ["in", [AGENT_ROLE, MANAGER_ROLE]], "parenttype": "User"}, pluck="parent")
	return [u for u in set(users) if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")]


def ensure_roles():
	"""after_migrate / after_install: the two help desk roles exist."""
	for role in (AGENT_ROLE, MANAGER_ROLE):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def _city():
	try:
		return frappe.db.get_single_value("App Setting", "city_name") or ""
	except Exception:
		return ""


def _sla_due(priority, start=None):
	return add_to_date(get_datetime(start) if start else now_datetime(), hours=SLA_HOURS.get(priority, 72))


# ---- permissions (hooks.py) ---------------------------------------------------------------------------------------
def ticket_conditions(user=None):
	user = user or frappe.session.user
	if is_agent(user):
		return ""
	return f"`tabSupport Ticket`.raised_by = {frappe.db.escape(user)}"


def ticket_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if is_agent(user) or ptype == "create":
		return True
	return doc.get("raised_by") == user or doc.get("owner") == user


def reply_conditions(user=None):
	user = user or frappe.session.user
	if is_agent(user):
		return ""
	u = frappe.db.escape(user)
	return f"(`tabSupport Ticket Reply`.is_internal = 0 and `tabSupport Ticket Reply`.ticket in (select name from `tabSupport Ticket` where raised_by = {u}))"


def reply_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if is_agent(user):
		return True
	if doc.get("is_internal"):
		return False
	return ptype == "create" or frappe.db.get_value(TICKET, doc.get("ticket"), "raised_by") == user


# ---- notifications ------------------------------------------------------------------------------------------------
def _notify(users, ticket, subject, from_user=None):
	"""One Notification Log (bell, push, email) per user, except the person who did it."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	for user in set(users):
		if not user or user == from_user or not frappe.db.get_value("User", user, "enabled"):
			continue
		enqueue_create_notification(
			[frappe.db.get_value("User", user, "email") or user],
			{
				"type": "Alert",
				"document_type": TICKET,
				"document_name": ticket.name,
				"subject": subject,
				"from_user": from_user,
				"link": frappe.utils.get_url(f"/janadhikara/support/{ticket.name}"),
			},
		)


# ---- reading ------------------------------------------------------------------------------------------------------
@frappe.whitelist()
def get_options():
	"""What the screens need to draw themselves: the lists, the signed-in user's part, and who can be assigned."""
	agents = [{"user": u, "name": frappe.db.get_value("User", u, "full_name") or u} for u in team_users()] if is_agent() else []
	return {
		"types": TYPES, "priorities": PRIORITIES, "statuses": STATUSES, "agents": agents,
		"is_agent": is_agent(), "is_manager": is_manager(), "city": _city(), "user": frappe.session.user,
	}


SORTS = {"modified": "modified desc", "created": "creation desc", "oldest": "creation asc", "due": "sla_due asc", "priority": "priority desc, modified desc"}


@frappe.whitelist()
def list_tickets(scope="mine", status=None, priority=None, ticket_type=None, assigned_to=None, search=None, overdue=0, sort="modified", start=0, page_length=25):
	"""scope: 'mine' (tickets I raised), 'queue' (agents: open work) or 'all' (agents: everything).
	Returns {rows, has_more}: one page, newest activity first unless `sort` says otherwise."""
	filters = {}
	if scope == "mine":
		filters["raised_by"] = frappe.session.user
	elif not is_agent():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	elif scope == "queue" and not status:
		filters["status"] = ["not in", list(CLOSED)]
	for key, value in (("status", status), ("priority", priority), ("ticket_type", ticket_type)):
		if value:
			filters[key] = ["in", value.split(",")] if "," in value else value  # several statuses: "Resolved,Closed"
	if int(overdue or 0):
		filters["sla_due"] = ["<", now_datetime()]
		filters["status"] = ["not in", list(CLOSED)]
	if assigned_to == "unassigned":
		filters["assigned_to"] = ["is", "not set"]
	elif assigned_to == "me":
		filters["assigned_to"] = frappe.session.user
	elif assigned_to:
		filters["assigned_to"] = assigned_to
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [["subject", "like", like], ["name", "like", like], ["raised_by_name", "like", like]]
	page_length = max(1, min(int(page_length), 100))
	rows = frappe.get_list(
		TICKET, fields=LIST_FIELDS, filters=filters, or_filters=or_filters,
		order_by=SORTS.get(sort, SORTS["modified"]), limit_start=int(start), limit_page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = rows[:page_length]
	now = now_datetime()
	names = {r.assigned_to for r in rows if r.assigned_to}
	full_names = {u: frappe.db.get_value("User", u, "full_name") for u in names}
	for r in rows:
		r["overdue"] = bool(r.sla_due and r.status not in CLOSED and get_datetime(r.sla_due) < now)
		r["assigned_name"] = full_names.get(r.assigned_to)
	return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_ticket(name):
	"""The ticket and its conversation (internal notes only for the team)."""
	doc = frappe.get_doc(TICKET, name)
	doc.check_permission("read")
	out = doc.as_dict()
	agent = is_agent()
	filters = {"ticket": name}
	if not agent:
		filters["is_internal"] = 0
	replies = frappe.get_all(REPLY, filters=filters, fields=["name", "message", "is_internal", "author", "creation", "to_users", "cc_users"], order_by="creation asc")
	for r in replies:
		r["html"] = _html(r["message"])
		r["to"] = _people(_tags(r.pop("to_users", None)))
		r["cc"] = _people(_tags(r.pop("cc_users", None)))
		r["author_name"] = frappe.db.get_value("User", r.author, "full_name") or r.author
		r["from_team"] = is_agent(r.author)
	out["replies"] = replies
	out["description_html"] = _html(doc.description)
	out["activity"] = _activity(name, agent)
	out["requester_email"] = frappe.db.get_value("User", doc.raised_by, "email") or doc.raised_by
	out["assigned_name"] = frappe.db.get_value("User", doc.assigned_to, "full_name") if doc.assigned_to else None
	out["overdue"] = bool(doc.sla_due and doc.status not in CLOSED and get_datetime(doc.sla_due) < now_datetime())
	out["can_work"] = agent
	out["recipients"] = _people(_recipients(doc)) if agent else []
	return out


def _activity(name, agent):
	"""The ticket's change log (from Version): who changed status, priority, type or assignee, and when. The requester
	sees status changes only."""
	shown = {"status": "Status", "priority": "Priority", "assigned_to": "Assignee", "ticket_type": "Type"}
	if not agent:
		shown = {"status": "Status"}
	events = []
	for v in frappe.get_all("Version", filters={"ref_doctype": TICKET, "docname": name}, fields=["owner", "creation", "data"], order_by="creation asc"):
		try:
			changed = frappe.parse_json(v.data).get("changed") or []
		except Exception:
			continue
		for field, old, new in changed:
			if field in shown:
				if field == "assigned_to":
					old, new = [frappe.db.get_value("User", u, "full_name") or u if u else None for u in (old, new)]
				events.append({"by": frappe.db.get_value("User", v.owner, "full_name") or v.owner, "user": v.owner, "creation": v.creation, "field": shown[field], "old": old, "new": new})
	return events


# ---- changing -----------------------------------------------------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def create_ticket(subject, ticket_type, description, priority="Medium", reference_doctype=None, reference_record=None, attachment=None):
	doc = frappe.get_doc({
		"doctype": TICKET, "subject": (subject or "").strip(), "ticket_type": ticket_type, "priority": priority,
		"description": description, "reference_doctype": reference_doctype or None,
		"reference_record": reference_record or None, "attachment": attachment or None,
	})
	doc.insert()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def add_reply(ticket, message, is_internal=0, to=None, cc=None):
	"""A reply on a ticket. The team's public reply moves Open to In Progress and stamps the first response; the
	requester's reply to a ticket waiting on them puts it back in progress (or reopens a resolved one)."""
	doc = frappe.get_doc(TICKET, ticket)
	doc.check_permission("read")
	agent = is_agent()
	is_internal = int(bool(int(is_internal or 0)))
	if is_internal and not agent:
		frappe.throw(_("Only the help desk team can write internal notes."), frappe.PermissionError)
	message = clean_html((message or "").strip())
	if not strip_html(message).strip() and "<img" not in message and "<a " not in message:
		frappe.throw(_("Write a message first."))
	# Who it is addressed to: the team chooses (the requester by default); the requester writes to the team
	allowed = _recipients(doc)
	if agent:
		to_users = _pick(to, allowed) if to is not None else [doc.raised_by]
		cc_users = [u for u in _pick(cc, allowed) if u not in to_users]
		if not to_users and not is_internal:
			frappe.throw(_("Add at least one person to the To line."))
	else:
		to_users, cc_users = [], []
	reply = frappe.get_doc({
		"doctype": REPLY, "ticket": ticket, "message": message, "is_internal": is_internal, "author": frappe.session.user,
		"to_users": ",".join(to_users), "cc_users": ",".join(cc_users),
	})
	reply.insert(ignore_permissions=True)
	if not is_internal:
		changes = {}
		if agent:
			if not doc.first_response_on:
				changes["first_response_on"] = now_datetime()
			if doc.status == "Open":
				changes["status"] = "In Progress"
		elif doc.status in ("Waiting on Requester", "Resolved"):
			changes["status"] = "In Progress"
		if changes:
			doc.update(changes)
			doc.flags.ignore_permissions = True
			doc.save()
		who = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
		if agent:
			_notify(to_users, doc, _("{0} replied to ticket {1}: {2}").format(who, doc.name, doc.subject), frappe.session.user)
			_notify(cc_users, doc, _("{0} copied you on ticket {1}: {2}").format(who, doc.name, doc.subject), frappe.session.user)
		else:
			_notify([doc.assigned_to] if doc.assigned_to else team_users(), doc, _("{0} replied on ticket {1}: {2}").format(who, doc.name, doc.subject), frappe.session.user)
	return {"name": reply.name}


@frappe.whitelist(methods=["POST"])
def update_ticket(name, status=None, priority=None, assigned_to=None, resolution=None):
	"""The team sets status, priority, assignee and resolution. The requester can only close their own ticket or
	reopen a resolved / closed one."""
	doc = frappe.get_doc(TICKET, name)
	doc.check_permission("read")
	if not is_agent():
		if status not in ("Closed", "Open") or any(v is not None for v in (priority, assigned_to, resolution)):
			frappe.throw(_("Not permitted."), frappe.PermissionError)
		if status == "Open" and doc.status not in CLOSED:
			frappe.throw(_("The ticket is not closed."))
	before_assignee, before_status = doc.assigned_to, doc.status
	if status:
		doc.status = status
	if priority:
		doc.priority = priority
	if assigned_to is not None:
		doc.assigned_to = assigned_to or None
		if assigned_to and doc.status == "Open" and not status:
			doc.status = "In Progress"
	if resolution is not None:
		doc.resolution = resolution
	doc.flags.ignore_permissions = True
	doc.save()
	me = frappe.session.user
	if doc.assigned_to and doc.assigned_to != before_assignee:
		_notify([doc.assigned_to], doc, _("Ticket {0} was assigned to you: {1}").format(doc.name, doc.subject), me)
	if doc.status != before_status:
		if is_agent():
			_notify([doc.raised_by], doc, _("Your ticket {0} is now {1}: {2}").format(doc.name, _(doc.status), doc.subject), me)
		else:
			_notify([doc.assigned_to] if doc.assigned_to else team_users(), doc, _("Ticket {0} was set to {1} by the requester").format(doc.name, _(doc.status)), me)
	return get_ticket(name)


def _people(users):
	"""[{user, name, email}] for the given users, skipping any that are gone."""
	out = []
	for u in users:
		row = frappe.db.get_value("User", u, ["full_name", "email"], as_dict=True)
		if row:
			out.append({"user": u, "name": row.full_name or u, "email": row.email or u})
	return out


def _recipients(doc):
	"""Who a reply can be addressed to: the requester and the help desk team. They are the people who can already see
	the ticket, so a reply never sends its text to anyone else."""
	return list(dict.fromkeys([doc.raised_by, *team_users()]))


def _pick(users, allowed):
	users = frappe.parse_json(users) if isinstance(users, str) else (users or [])
	picked = [u for u in dict.fromkeys(users) if u in allowed]
	if len(picked) != len(list(dict.fromkeys(users))):
		frappe.throw(_("A reply can only be addressed to the requester or the help desk team."))
	return picked


@frappe.whitelist(methods=["POST"])
def delete_tickets(names):
	"""Managers delete tickets (with their replies and tags)."""
	if not is_manager():
		frappe.throw(_("Only a help desk manager can delete tickets."), frappe.PermissionError)
	names = frappe.parse_json(names) if isinstance(names, str) else names
	deleted = 0
	for name in names or []:
		if not frappe.db.exists(TICKET, name):
			continue
		frappe.db.delete(REPLY, {"ticket": name})
		frappe.db.delete("Tag Link", {"document_type": TICKET, "document_name": name})
		frappe.delete_doc(TICKET, name, ignore_permissions=True, force=True)
		deleted += 1
	return {"deleted": deleted}


@frappe.whitelist()
def get_overview():
	"""Manager view: how the help desk is doing."""
	if not is_manager():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	now = now_datetime()
	opened = {"status": ["not in", list(CLOSED)]}
	count = lambda extra=None: frappe.db.count(TICKET, {**opened, **(extra or {})})
	open_sql = "status not in ('Resolved', 'Closed')"
	by = lambda field: {k or "-": v for k, v in frappe.db.sql(f"select `{field}`, count(*) from `tabSupport Ticket` where {open_sql} group by `{field}`")}
	overdue = frappe.db.count(TICKET, {**opened, "sla_due": ["<", now]})
	since = add_to_date(now, days=-90)
	rows = frappe.get_all(TICKET, filters={"creation": [">", since]}, fields=["creation", "first_response_on", "resolved_on", "status"])
	hours = lambda a, b: (get_datetime(b) - get_datetime(a)).total_seconds() / 3600
	first = [hours(r.creation, r.first_response_on) for r in rows if r.first_response_on]
	resolved = [hours(r.creation, r.resolved_on) for r in rows if r.resolved_on]
	load = frappe.db.sql(f"select assigned_to, count(*) from `tabSupport Ticket` where {open_sql} and ifnull(assigned_to, '') != '' group by assigned_to")
	days = []
	for i in range(13, -1, -1):
		day = add_to_date(now, days=-i).date()
		days.append({
			"date": str(day),
			"created": frappe.db.count(TICKET, {"creation": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]}),
			"resolved": frappe.db.count(TICKET, {"resolved_on": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]}),
		})
	return {
		"open": count(), "unassigned": count({"assigned_to": ["is", "not set"]}), "overdue": overdue,
		"urgent": count({"priority": "Urgent"}), "waiting": count({"status": "Waiting on Requester"}),
		"by_status": by("status"), "by_priority": by("priority"), "by_type": by("ticket_type"),
		"avg_first_response_hours": round(sum(first) / len(first), 1) if first else None,
		"avg_resolution_hours": round(sum(resolved) / len(resolved), 1) if resolved else None,
		"agent_load": [{"user": u, "name": frappe.db.get_value("User", u, "full_name") or u, "open": n} for u, n in load],
		"days": days,
	}
