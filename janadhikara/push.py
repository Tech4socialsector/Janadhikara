"""Web Push: alerts that reach a user's phone or desktop even when the app is closed.

How it works (no extra libraries):
- The server holds a VAPID key pair (made on first use, kept in App Setting).
- A browser that allows alerts registers a Push Subscription (its push address).
- When a Notification Log is created for a user, the server pings each of their
  subscriptions, signed with VAPID. The ping carries no text; the service worker
  (push-sw.js) wakes up, fetches the user's latest notification and shows it.
  Nothing personal ever travels through the browser vendor's push service.
"""

import base64
import json
import time
from urllib.parse import urlparse

import frappe
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

SUBJECT = "mailto:tech4socialsector@azimpremjifoundation.org"


def _b64(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _public_bytes(private_key) -> bytes:
	return private_key.public_key().public_bytes(
		serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
	)


def get_vapid_keys():
	"""(private_key object, public key string), creating the pair the first time."""
	settings = frappe.get_single("App Setting")
	pem = settings.get_password("push_private_key", raise_exception=False)
	if pem and settings.push_public_key:
		return serialization.load_pem_private_key(pem.encode(), password=None), settings.push_public_key

	key = ec.generate_private_key(ec.SECP256R1())
	settings.push_private_key = key.private_bytes(
		serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
	).decode()
	settings.push_public_key = _b64(_public_bytes(key))
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.db.commit()
	return key, settings.push_public_key


def vapid_headers(endpoint: str, private_key, public_key: str, now: int | None = None) -> dict:
	parsed = urlparse(endpoint)
	claims = {
		"aud": f"{parsed.scheme}://{parsed.netloc}",
		"exp": int(now or time.time()) + 12 * 3600,
		"sub": SUBJECT,
	}
	signing_input = (
		_b64(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
		+ "."
		+ _b64(json.dumps(claims, separators=(",", ":")).encode())
	)
	r, s = decode_dss_signature(private_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
	token = f"{signing_input}.{_b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
	return {
		"Authorization": f"vapid t={token}, k={public_key}",
		"TTL": "3600",
		"Urgency": "high",
		"Content-Length": "0",
	}


# --- API ------------------------------------------------------------------------
@frappe.whitelist()
def get_push_config():
	"""The public key a browser needs to subscribe."""
	return {"public_key": get_vapid_keys()[1]}


# Browsers hand out push addresses on their vendor's push service. The server later POSTs to
# whatever address is stored, so only those services are accepted (never an arbitrary URL -
# that would let a user make the server call internal addresses).
PUSH_HOST_SUFFIXES = (
	".googleapis.com",  # Chrome / Edge / Opera / Brave (FCM)
	".push.services.mozilla.com",  # Firefox
	".push.apple.com",  # Safari
	".notify.windows.com",  # Windows (WNS)
)


def is_valid_push_endpoint(endpoint: str) -> bool:
	try:
		parsed = urlparse(endpoint)
	except ValueError:
		return False
	host = (parsed.hostname or "").lower()
	return (
		parsed.scheme == "https"
		and not parsed.username
		and parsed.port in (None, 443)
		and any(host.endswith(suffix) or host == suffix.lstrip(".") for suffix in PUSH_HOST_SUFFIXES)
	)


@frappe.whitelist(methods=["POST"])
def save_push_subscription(endpoint: str, user_agent: str | None = None):
	"""Remember this browser's push address for the signed-in user."""
	user = frappe.session.user
	if user == "Guest" or not endpoint:
		frappe.throw(frappe._("Not allowed"), frappe.PermissionError)
	if not is_valid_push_endpoint(endpoint):
		frappe.throw(frappe._("That is not a valid push address."), frappe.ValidationError)
	existing = frappe.db.get_value("Push Subscription", {"endpoint": endpoint}, "name")
	if existing:
		frappe.db.set_value("Push Subscription", existing, "user", user)
		return existing
	doc = frappe.get_doc(
		{"doctype": "Push Subscription", "user": user, "endpoint": endpoint, "user_agent": (user_agent or "")[:140]}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def remove_push_subscription(endpoint: str):
	name = frappe.db.get_value("Push Subscription", {"endpoint": endpoint, "user": frappe.session.user}, "name")
	if name:
		frappe.delete_doc("Push Subscription", name, ignore_permissions=True)


# --- Sending --------------------------------------------------------------------
def notification_created(doc, method=None):
	"""Notification Log after_insert: ping the user's devices."""
	from frappe.desk.doctype.notification_settings.notification_settings import is_notifications_enabled

	if doc.for_user and is_notifications_enabled(doc.for_user):
		frappe.enqueue("janadhikara.push.send_to_user", user=doc.for_user, enqueue_after_commit=True, queue="short")


def send_to_user(user: str):
	subscriptions = frappe.get_all("Push Subscription", filters={"user": user}, fields=["name", "endpoint"])
	if not subscriptions:
		return
	private_key, public_key = get_vapid_keys()
	for sub in subscriptions:
		if not is_valid_push_endpoint(sub.endpoint):
			frappe.delete_doc("Push Subscription", sub.name, ignore_permissions=True)
			continue
		try:
			response = requests.post(
				sub.endpoint,
				headers=vapid_headers(sub.endpoint, private_key, public_key),
				timeout=10,
				allow_redirects=False,
			)
			if response.status_code in (404, 410):  # the browser dropped this subscription
				frappe.delete_doc("Push Subscription", sub.name, ignore_permissions=True)
			elif response.status_code >= 400:
				frappe.log_error(f"Push to {sub.name} failed: {response.status_code} {response.text[:200]}", "Web Push")
		except Exception:
			frappe.log_error(title="Web Push failed")
	frappe.db.commit()
