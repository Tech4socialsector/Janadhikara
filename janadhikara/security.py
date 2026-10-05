"""Response hardening for every request this app serves (after_request hook)."""


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
