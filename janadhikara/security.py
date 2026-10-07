"""Response hardening for every request this app serves (after_request hook), and the
per-partner data isolation of Household Profile, Individual Profile and Settlement."""

import frappe


def add_security_headers(response=None, request=None):
	if response is None:
		return
	headers = response.headers
	headers.setdefault("X-Content-Type-Options", "nosniff")
	headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
	headers.setdefault("X-Frame-Options", "SAMEORIGIN")
	# The app uses the microphone (voice input) and location (maps) on its own pages only.
	headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=(self), payment=()")
	if request is not None and (request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"):
		headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
	path = getattr(request, "path", "") or ""
	if path.startswith("/api/") and "Cache-Control" not in headers:
		# Private, per-user data: never kept by a shared cache or proxy.
		headers["Cache-Control"] = "private, no-store"


# --- Per-partner data isolation --------------------------------------------------------------
# A worker sees and edits only the records of their own partner organisation. The programme team
# (System Manager, Program Coordinator, Program Manager) sees every partner; a Report Viewer who is
# not a partner worker (programme-side reviewer) can read every partner.

PROGRAMME_ROLES = {"System Manager", "Program Coordinator", "Program Manager"}
PARTNER_FIELD = {"Household Profile": "partner_organization", "Settlement": "partner_organization", "Individual Profile": "implementing_org"}


def user_scope(user=None):
	"""("all", None) | ("partner", <partner name>) | ("none", None) for the user - worked out once per request."""
	user = user or frappe.session.user
	cache = getattr(frappe.local, "janadhikara_scope", None)
	if cache is None:
		cache = frappe.local.janadhikara_scope = {}
	if user in cache:
		return cache[user]
	if user == "Administrator":
		scope = ("all", None)
	else:
		roles = set(frappe.get_roles(user))
		if roles & PROGRAMME_ROLES:
			scope = ("all", None)
		else:
			from janadhikara.api import get_user_employee

			employee = get_user_employee(user)
			if employee:
				scope = ("partner", employee.parent)
			elif "Report Viewer" in roles:
				scope = ("all", None)
			else:
				scope = ("none", None)
	cache[user] = scope
	return scope


def _query_conditions(doctype, user=None):
	kind, partner = user_scope(user)
	if kind == "all":
		return ""
	if kind == "none":
		return "1=0"
	return f"`tab{doctype}`.`{PARTNER_FIELD[doctype]}` = {frappe.db.escape(partner)}"


def _has_permission(doc, doctype, user=None, permission_type=None):
	"""Controller hooks can only deny; this version of Frappe treats anything but True as a denial."""
	kind, partner = user_scope(user)
	if kind == "all":
		return True  # normal role permissions decide
	if kind == "none":
		return False
	owner_partner = doc.get(PARTNER_FIELD[doctype])
	if not owner_partner:
		return True  # a record not yet tied to a partner (being created)
	return owner_partner == partner


def household_conditions(user=None, **kwargs):
	return _query_conditions("Household Profile", user)


def settlement_conditions(user=None, **kwargs):
	return _query_conditions("Settlement", user)


def individual_conditions(user=None, **kwargs):
	return _query_conditions("Individual Profile", user)


def household_has_permission(doc, ptype=None, user=None, **kwargs):
	return _has_permission(doc, "Household Profile", user, ptype)


def settlement_has_permission(doc, ptype=None, user=None, **kwargs):
	return _has_permission(doc, "Settlement", user, ptype)


def individual_has_permission(doc, ptype=None, user=None, **kwargs):
	return _has_permission(doc, "Individual Profile", user, ptype)


def enforce_own_partner(doc):
	"""On save: a partner worker may only create or change records of their own partner."""
	kind, partner = user_scope()
	if kind != "partner":
		return
	value = doc.get(PARTNER_FIELD[doc.doctype])
	if value and value != partner:
		frappe.throw(frappe._("You can only work with records of your own partner organisation."), frappe.PermissionError)


def can_read_parent(parenttype, parent):
	"""May the user read this one parent record (a child row is as readable as its parent)?
	Partner workers see only the workers (rows) of their own partner organisation."""
	if not parenttype or not parent:
		return False
	if not frappe.has_permission(parenttype, "read", doc=parent):
		return False
	if parenttype == "Partner Details":
		kind, partner = user_scope()
		if kind == "partner":
			return parent == partner
		if kind == "none":
			return False
	return True


# --- Secrets in Error Log ----------------------------------------------------------------------
# Frappe's tracebacks list the local variables of every frame, which can include an API key that was
# being used when something failed. Anything that looks like a key is blanked before an Error Log is saved.

import re

_SECRET_PATTERNS = (
	(re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer [hidden]"),
	(re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}"), "[hidden key]"),
	(re.compile(r"(?i)((?:api[_-]?key|authorization|x-api-key|secret|password)['\"]?\s*[:=]\s*['\"]?)([^'\"\s,}\]]{6,})"), r"\1[hidden]"),
)


def scrub_secrets(text):
	if not text:
		return text
	try:
		key = frappe.get_single("App Setting").get_password("ai_api_key", raise_exception=False)
		if key and len(key) >= 8:
			text = text.replace(key, "[hidden key]")
	except Exception:
		pass
	for pattern, replacement in _SECRET_PATTERNS:
		text = pattern.sub(replacement, text)
	return text


def scrub_error_log(doc, method=None):
	doc.error = scrub_secrets(doc.error)
	if doc.get("method"):
		doc.method = scrub_secrets(doc.method)
