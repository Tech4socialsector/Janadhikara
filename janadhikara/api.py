from io import BytesIO

import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from frappe.utils.file_manager import get_file_path
from PIL import Image


PRIVILEGED_ROLES = {'Administrator', 'System Manager', 'Program Coordinator'}


@frappe.whitelist(allow_guest=True)
def get_app_branding():
    """Return the Janadhikara Vue app's configurable logo/name/login text, set from
    the desk via App Setting, for the header and login page to render.
    app_logo_dark falls back to app_logo itself when left blank, so the
    frontend can always just pick whichever of the two matches the active
    theme without its own separate fallback logic."""
    settings = frappe.get_single('App Setting')
    return {
        'app_name': settings.app_name or 'Janadhikara',
        'app_logo': settings.app_logo or None,
        'app_logo_dark': settings.app_logo_dark or settings.app_logo or None,
        'login_headline': settings.login_headline or None,
        'login_description': settings.login_description or None,
        'accent_color': settings.accent_color or None,
    }


PWA_ICON_SIZES = [64, 192, 512]


@frappe.whitelist(allow_guest=True)
def get_pwa_manifest():
    """Serve the Web App Manifest with icons pointing at App Setting.app_logo
    (resized on request by get_pwa_icon below) instead of the static PNGs
    vite-plugin-pwa bakes in at build time - so a PWA install picks up
    whatever logo is actually configured, not whatever was uploaded when the
    app was last built. Most phones only fetch icons at install time, so
    changing the logo later won't update an already-installed icon without a
    reinstall - there's no push mechanism for that on any platform."""
    settings = frappe.get_single('App Setting')
    app_name = settings.app_name or 'Janadhikara'
    icon_version = _app_logo_cache_key(settings.app_logo)

    icons = [
        {
            'src': f'/api/method/janadhikara.api.get_pwa_icon?size={size}&v={icon_version}',
            'sizes': f'{size}x{size}',
            'type': 'image/png',
        }
        for size in PWA_ICON_SIZES
    ]
    icons.append({
        'src': f'/api/method/janadhikara.api.get_pwa_icon?size=512&maskable=1&v={icon_version}',
        'sizes': '512x512',
        'type': 'image/png',
        'purpose': 'maskable',
    })

    manifest = {
        'id': '/janadhikara/',
        'name': app_name,
        'short_name': app_name,
        'description': 'Community health worker data capture and follow-up tracking.',
        'start_url': '/janadhikara/',
        'scope': '/janadhikara/',
        'display': 'standalone',
        'background_color': '#ffffff',
        'theme_color': '#111827',
        'icons': icons,
    }

    frappe.response['type'] = 'download'
    frappe.response['filename'] = 'manifest.webmanifest'
    frappe.response['filecontent'] = frappe.as_json(manifest)
    frappe.response['content_type'] = 'application/manifest+json'
    frappe.response['display_content_as'] = 'inline'


def _app_logo_cache_key(app_logo):
    """A cache/URL-busting key that changes exactly when the logo does -
    the logo's own path already changes on every re-upload (Frappe names
    uploaded files uniquely), so it doubles as a fingerprint with no extra
    bookkeeping needed."""
    return frappe.utils.sha256_hash(app_logo or 'default')[:12]


@frappe.whitelist(allow_guest=True)
def get_pwa_icon(size='512', maskable=None):
    """Resize App Setting.app_logo into a square PNG at the requested size
    for the PWA manifest (see get_pwa_manifest) - phones expect specific
    icon sizes in specific formats, so the raw uploaded logo (whatever
    aspect ratio/format an admin uploaded) can't be linked directly.
    maskable=1 additionally pads the image to a safe zone on a solid
    background, per the maskable icon spec, so platforms that crop PWA
    icons into a circle/squircle don't cut off the logo's edges."""
    size = frappe.utils.cint(size) or 512
    if size not in PWA_ICON_SIZES:
        size = min(PWA_ICON_SIZES, key=lambda s: abs(s - size))
    is_maskable = frappe.utils.cint(maskable) == 1

    settings = frappe.get_single('App Setting')
    cache_key = f'pwa-icon:{_app_logo_cache_key(settings.app_logo)}:{size}:{int(is_maskable)}'
    cached = frappe.cache().get_value(cache_key)

    if cached is None:
        cached = _render_pwa_icon(settings.app_logo, size, is_maskable)
        frappe.cache().set_value(cache_key, cached, expires_in_sec=3600)

    frappe.response['type'] = 'download'
    frappe.response['filename'] = f'pwa-icon-{size}.png'
    frappe.response['filecontent'] = cached
    frappe.response['content_type'] = 'image/png'
    frappe.response['display_content_as'] = 'inline'


def _render_pwa_icon(app_logo, size, is_maskable):
    source = None
    if app_logo:
        try:
            with open(get_file_path(app_logo), 'rb') as f:
                source = Image.open(f)
                source.load()
        except Exception:
            frappe.log_error(title='PWA icon: failed to read App Setting.app_logo')
            source = None

    if source is None:
        # No logo configured (or it failed to load) - a plain colored
        # square beats a broken image in the install prompt/home screen.
        canvas = Image.new('RGB', (size, size), '#111827')
    else:
        source = source.convert('RGBA')
        # Center-crop to square before scaling, so an arbitrary-aspect-ratio
        # upload (a wide logo, a tall one) doesn't get squashed.
        w, h = source.size
        edge = min(w, h)
        left, top = (w - edge) // 2, (h - edge) // 2
        source = source.crop((left, top, left + edge, top + edge))

        if is_maskable:
            # Maskable icons must keep their subject inside an ~80% "safe
            # zone" - platforms that crop into a circle/squircle shape may
            # cut off anything closer to the edge than that.
            safe_size = int(size * 0.8)
            source = source.resize((safe_size, safe_size), Image.LANCZOS)
            corner = source.getpixel((0, 0))
            fill = corner[:3] if isinstance(corner, tuple) else (17, 24, 39)
            canvas = Image.new('RGB', (size, size), fill)
            offset = (size - safe_size) // 2
            canvas.paste(source, (offset, offset), source)
        else:
            source = source.resize((size, size), Image.LANCZOS)
            canvas = Image.new('RGB', (size, size), '#ffffff')
            canvas.paste(source, (0, 0), source)

    buffer = BytesIO()
    canvas.save(buffer, format='PNG')
    return buffer.getvalue()


@frappe.whitelist()
def search_list(doctype, search_term, fields, search_fields):
    """OR-search search_term across search_fields, returning the given
    fields - the mobile list view's single search box (replacing several
    stacked per-field filters, which don't fit well on a small screen) needs
    to match any one of several fields at once. The v2 REST document-list
    endpoint DoctypeList.vue otherwise uses (/api/v2/document/<doctype>)
    only takes `filters`, which Frappe always ANDs together field-by-field -
    there's no way to express "Village OR Head of Family OR ..." through it.
    frappe.get_list's or_filters parameter (unlike that REST endpoint) does
    support this directly. Runs with the same permission enforcement as any
    other list fetch (frappe.get_list checks doctype/row permissions itself,
    same as DoctypeList's normal query) - no extra doctype allowlist here,
    since this can't do anything a permitted, filtered list fetch couldn't."""
    fields = frappe.parse_json(fields)
    search_fields = frappe.parse_json(search_fields)
    search_term = (search_term or '').strip()

    if not search_term or not search_fields:
        return frappe.get_list(doctype, fields=fields, limit_page_length=20, order_by='modified desc')

    or_filters = [[field, 'like', f'%{search_term}%'] for field in search_fields]
    return frappe.get_list(
        doctype,
        fields=fields,
        or_filters=or_filters,
        limit_page_length=20,
        order_by='modified desc',
    )


SYSTEM_ADMIN_ROLES = {'Administrator', 'System Manager'}


@frappe.whitelist()
def get_current_user_context():
    """Return whether the logged-in user has a privileged (System Manager /
    Program Coordinator / Administrator) role, so the Vue app can show or
    hide privileged-only UI (e.g. the App Settings dialog) without exposing
    the full role list. `is_system_admin` is the narrower System Manager /
    Administrator check, for UI that's more sensitive than general app
    content settings (e.g. email server configuration)."""
    user_roles = set(frappe.get_roles())
    return {
        'is_privileged': bool(PRIVILEGED_ROLES & user_roles),
        'is_system_admin': bool(SYSTEM_ADMIN_ROLES & user_roles),
    }


def module_visible_to_user(module_doc, user_roles):
    """An App Module Setting doc is visible if enabled and either
    role-restriction is off or its `roles` child table shares at least one
    role with the current user."""
    if not module_doc.enabled:
        return False
    if not module_doc.restrict_by_role:
        return True
    allowed_roles = {r.role for r in (module_doc.roles or [])}
    return bool(allowed_roles & user_roles)


@frappe.whitelist()
def get_app_modules():
    """Return the Janadhikara Vue app's navigation modules (from the standalone App
    Module Setting doctype), filtered to those enabled and visible to the
    current user's roles. Each module lists the sidebar DocTypes it exposes."""
    if frappe.session.user == 'Guest':
        frappe.throw(_('Not permitted'), frappe.PermissionError)

    user_roles = set(frappe.get_roles())
    names = frappe.get_all('App Module Setting', pluck='name', order_by='sort_order asc')

    modules = []
    for name in names:
        module_doc = frappe.get_cached_doc('App Module Setting', name)
        if not module_visible_to_user(module_doc, user_roles):
            continue
        doctypes = [
            {
                'doctype_name': item.doctype_name,
                'label': item.label or item.doctype_name,
                'icon': item.icon or module_doc.icon or 'file-text',
                'route': item.route or frappe.scrub(item.doctype_name).replace('_', '-'),
            }
            for item in (module_doc.doctypes or [])
            if item.doctype_name
        ]
        if not doctypes:
            continue
        modules.append({
            'label': module_doc.label,
            'icon': module_doc.icon or 'file-text',
            'doctypes': doctypes,
        })
    return modules


def announcement_visible_to_user(announcement_doc, user_roles, user):
    """An Announcement is visible if enabled, within its optional start/end
    date window, and either shown to everyone or the current user matches
    its role/user targeting."""
    if not announcement_doc.enabled:
        return False
    today = getdate(nowdate())
    if announcement_doc.start_date and getdate(announcement_doc.start_date) > today:
        return False
    if announcement_doc.end_date and getdate(announcement_doc.end_date) < today:
        return False
    if announcement_doc.audience == 'Specific Roles':
        allowed_roles = {r.role for r in (announcement_doc.roles or [])}
        return bool(allowed_roles & user_roles)
    if announcement_doc.audience == 'Specific Users':
        allowed_users = {u.user for u in (announcement_doc.users or [])}
        return user in allowed_users
    return True


@frappe.whitelist()
def get_active_announcements():
    """Return Announcements currently active and targeted at the logged-in
    user (by role or specific user, or shown to everyone), excluding any
    the user has already dismissed."""
    if frappe.session.user == 'Guest':
        return []

    user = frappe.session.user
    user_roles = set(frappe.get_roles())
    dismissed = set(
        frappe.get_all(
            'Announcement Dismissal',
            filters={'user': user},
            pluck='announcement',
        )
    )

    names = frappe.get_all('Announcement', pluck='name', order_by='creation desc')
    announcements = []
    for name in names:
        if name in dismissed:
            continue
        doc = frappe.get_cached_doc('Announcement', name)
        if not announcement_visible_to_user(doc, user_roles, user):
            continue
        announcements.append({
            'name': doc.name,
            'title': doc.title,
            'message': doc.message,
            'announcement_type': doc.announcement_type,
            'dismissible': doc.dismissible,
        })
    return announcements


@frappe.whitelist()
def dismiss_announcement(name):
    """Record that the logged-in user has dismissed an Announcement, so
    get_active_announcements stops returning it for them."""
    if frappe.session.user == 'Guest':
        frappe.throw(_('Not permitted'), frappe.PermissionError)

    user = frappe.session.user
    if not frappe.db.exists('Announcement Dismissal', {'announcement': name, 'user': user}):
        frappe.get_doc({
            'doctype': 'Announcement Dismissal',
            'announcement': name,
            'user': user,
        }).insert(ignore_permissions=True)
        frappe.db.commit()


@frappe.whitelist()
def global_search(txt):
    """Search across every DocType configured in the app's modules (App
    Module Setting -> doctypes), respecting the user's normal doc
    permissions on each. Used by the Vue app's navbar search box."""
    from frappe.desk.search import search_link

    txt = (txt or '').strip()
    if not txt or frappe.session.user == 'Guest':
        return []

    user_roles = set(frappe.get_roles())
    module_names = frappe.get_all('App Module Setting', pluck='name')

    seen_doctypes = set()
    doctype_routes = {}
    for module_name in module_names:
        module_doc = frappe.get_cached_doc('App Module Setting', module_name)
        if not module_visible_to_user(module_doc, user_roles):
            continue
        for item in (module_doc.doctypes or []):
            if not item.doctype_name or item.doctype_name in seen_doctypes:
                continue
            seen_doctypes.add(item.doctype_name)
            doctype_routes[item.doctype_name] = item.route or frappe.scrub(item.doctype_name).replace('_', '-')

    results = []
    for doctype_name in seen_doctypes:
        try:
            matches = search_link(doctype_name, txt, page_length=5)
        except (frappe.PermissionError, frappe.DoesNotExistError):
            continue
        for match in matches:
            results.append({
                'doctype_name': doctype_name,
                'route': doctype_routes[doctype_name],
                'name': match.get('value'),
                'description': match.get('description'),
            })

    return results[:30]


def validate_phone_number(phone_number):
    """Raise if phone_number contains anything other than digits."""
    if phone_number and not phone_number.isdigit():
        frappe.throw(_('Phone Number must contain digits only'))

