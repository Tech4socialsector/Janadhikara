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
    # A logged-in partner employee sees their own partner's logo (Partner
    # Details > Partner Logo); everyone else - and any partner without one -
    # gets the App Setting logo as the fallback.
    partner_logo = get_user_partner_logo()
    return {
        'app_name': settings.app_name or 'Janadhikara',
        'app_logo': partner_logo or settings.app_logo or None,
        'app_logo_dark': partner_logo or settings.app_logo_dark or settings.app_logo or None,
        'login_headline': settings.login_headline or None,
        'login_description': settings.login_description or None,
        'accent_color': settings.accent_color or None,
    }


def get_user_partner_logo():
    """Logo of the Partner Details the logged-in user works for (matched by
    the Employee row's User, or its Email), or None when they belong to no
    partner or their partner has no logo."""
    user = frappe.session.user
    if user == 'Guest':
        return None
    rows = frappe.db.sql(
        """
        select pd.partner_logo
        from `tabEmployee` e
        join `tabPartner Details` pd on pd.name = e.parent
        where e.parenttype = 'Partner Details'
          and (e.user = %(user)s or e.email = %(user)s)
          and ifnull(e.status, 'Active') = 'Active'
          and ifnull(pd.partner_logo, '') != ''
        order by pd.modified desc
        limit 1
        """,
        {'user': user},
    )
    return rows[0][0] if rows else None


@frappe.whitelist(allow_guest=True)
def get_login_options():
    """What the login page should offer besides email + password: one entry
    per enabled Social Login Key (Google, GitHub, Office 365, Frappe, custom
    OAuth2 ...), built the same way Frappe's own login page builds them
    (frappe/www/login.py), so single sign-on configured in Social Login Key
    just works here. A successful sign-in lands on Home.
    `disable_user_pass_login` mirrors System Settings. Shape: { providers:
    [{ name, label, icon, auth_url }], disable_user_pass_login, app_version }."""
    from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys

    redirect_to = '/janadhikara/home'
    providers = []
    for provider in frappe.get_all(
        'Social Login Key',
        filters={'enable_social_login': 1},
        fields=['name', 'client_id', 'base_url', 'provider_name', 'icon'],
        order_by='creation asc',
    ):
        # Same eligibility test as Frappe's login page: needs a client id, a
        # base url and a stored client secret, or the sign-in couldn't work.
        if not (provider.client_id and provider.base_url and get_oauth_keys(provider.name)):
            continue
        try:
            auth_url = get_oauth2_authorize_url(provider.name, redirect_to)
        except Exception:
            frappe.log_error(title=f'Login: could not build SSO link for {provider.name}')
            continue
        icon = provider.icon if provider.provider_name != 'Custom' else None
        providers.append({
            'name': provider.name,
            'label': provider.provider_name if provider.provider_name != 'Custom' else provider.name,
            'icon': icon,
            'auth_url': auth_url,
        })

    import janadhikara

    return {
        'providers': providers,
        'disable_user_pass_login': bool(frappe.utils.cint(frappe.get_system_settings('disable_user_pass_login'))),
        # Single source of truth: janadhikara/__init__.py (pyproject.toml reads it too).
        'app_version': janadhikara.__version__,
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
        # Opens straight on Home, in its own window with no browser UI (no URL
        # bar, tabs or browser menu) - like an app installed from a store.
        'start_url': '/janadhikara/home',
        'scope': '/janadhikara/',
        'display': 'standalone',
        'display_override': ['standalone', 'minimal-ui'],
        # Re-use the open window when launched again instead of stacking tabs.
        'launch_handler': {'client_mode': ['navigate-existing', 'auto']},
        'background_color': '#ffffff',
        'theme_color': '#ffffff',
        'lang': 'en',
        'dir': 'ltr',
        'categories': ['health', 'productivity'],
        'prefer_related_applications': False,
        'icons': icons,
        # Long-press the home-screen icon for quick jumps.
        'shortcuts': [
            {'name': 'Home', 'url': '/janadhikara/home', 'icons': [icons[1]]},
            {'name': 'Worklist', 'url': '/janadhikara/worklist', 'icons': [icons[1]]},
        ],
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
        # No logo configured (or it failed to load): Janadhikara's own icon,
        # shipped in the app's public folder.
        try:
            default_path = frappe.get_app_path('janadhikara', 'public', 'default-logo.png')
            source = Image.open(default_path)
            source.load()
        except Exception:
            frappe.log_error(title='PWA icon: failed to read the bundled default logo')
            source = None

    if source is None:
        # Last resort - a plain colored square beats a broken image in the
        # install prompt/home screen.
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
            if isinstance(corner, tuple) and len(corner) == 4 and corner[3] < 255:
                # Transparent corner (a rounded-square logo): sample the logo's
                # own background just inside its top edge instead.
                corner = source.getpixel((safe_size // 2, max(2, safe_size // 40)))
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


# Settings dialog catalog: (doctype, group, icon, description). Only entries
# whose doctype exists and that the user has read permission on are returned
# by get_settings_entries, so the dialog shows exactly what their roles allow.
SETTINGS_CATALOG = [
    ('App Setting', 'Application', 'sliders', 'General application settings.'),
    ('PNC Visit Interval Master', 'Application', 'calendar', 'Visit intervals used for PNC scheduling.'),
    ('Field Function Mapping', 'Application', 'wand-sparkles', 'Tag built-in functions (like map shape capture) to form fields.'),
    ('AI Data Policy', 'Application', 'shield-check', 'What the AI assistant may read or change, and which fields it can never see.'),
    ('Announcement', 'Content', 'megaphone', 'Banners shown to users on the Home page.'),
    ('AI Guide Section', 'Content', 'book-open', 'Guide content the AI assistant answers from.'),
    ('App Module Setting', 'Access', 'layout-grid', 'Modules, sidebar items and which roles can see them.'),
]


@frappe.whitelist()
def get_settings_entries():
    """Return the Settings dialog entries the current user's role permissions
    allow. Single doctypes are edited inline; list doctypes are managed in
    Frappe desk (the SPA only has list pages for doctypes registered in an
    App Module Setting)."""
    if frappe.session.user == 'Guest':
        frappe.throw(_('Not permitted'), frappe.PermissionError)

    entries = []
    for doctype, group, icon, description in SETTINGS_CATALOG:
        if not frappe.db.exists('DocType', doctype):
            continue
        if not frappe.has_permission(doctype, 'read'):
            continue
        meta = frappe.get_meta(doctype)
        is_single = bool(meta.issingle)
        entries.append({
            'key': frappe.scrub(doctype),
            'doctype': doctype,
            'label': doctype,
            'group': group,
            'icon': icon,
            'description': description,
            'is_single': is_single,
            'can_write': bool(frappe.has_permission(doctype, 'write')),
            'can_create': (not is_single) and bool(frappe.has_permission(doctype, 'create')),
            'desk_route': frappe.scrub(doctype).replace('_', '-'),
            'count': None if is_single else frappe.db.count(doctype),
        })
    return entries


SEARCHABLE_FIELDTYPES = {'Data', 'Small Text', 'Text', 'Long Text', 'Select', 'Link', 'Int', 'Float', 'Phone', 'Date', 'Datetime'}


@frappe.whitelist()
def search_record_names(doctype, txt, limit=500):
    """Names of `doctype` records matching `txt` anywhere a person would look:
    the record ID, its title, any of its own text-like fields, and the
    text-like fields of rows in its child tables (so searching a Settlement
    finds it by the name of one of its Intervention Units). Only a candidate
    list - the list view still fetches the records themselves through normal
    permission-checked queries."""
    txt = (txt or '').strip()
    if not txt:
        return []
    if not frappe.has_permission(doctype, 'read'):
        frappe.throw(_('Not permitted'), frappe.PermissionError)

    pattern = f'%{txt}%'
    limit = min(int(limit), 1000)
    meta = frappe.get_meta(doctype)

    def text_fields(m):
        return [
            df.fieldname
            for df in m.fields
            if df.fieldtype in SEARCHABLE_FIELDTYPES and not df.hidden
        ]

    names = set()

    own_filters = [[doctype, 'name', 'like', pattern]] + [
        [doctype, fieldname, 'like', pattern] for fieldname in text_fields(meta)
    ]
    names.update(frappe.get_list(doctype, or_filters=own_filters, pluck='name', limit_page_length=limit))

    for table_field in meta.get_table_fields():
        child_meta = frappe.get_meta(table_field.options)
        child_filters = [[table_field.options, fieldname, 'like', pattern] for fieldname in text_fields(child_meta)]
        if not child_filters:
            continue
        names.update(
            frappe.get_all(
                table_field.options,
                filters={'parenttype': doctype, 'parentfield': table_field.fieldname},
                or_filters=child_filters,
                pluck='parent',
                limit_page_length=limit,
            )
        )
    return list(names)[:limit]


def get_user_employee(user=None):
    """The Employee (partner worker) row for `user` (default: logged in),
    matched by its User link or its Email, active ones only. None for anyone
    who isn't a partner worker (e.g. an administrator)."""
    user = user or frappe.session.user
    if user in ('Guest', 'Administrator'):
        return None
    rows = frappe.db.sql(
        """
        select e.name, e.parent, e.worker_name
        from `tabEmployee` e
        where e.parenttype = 'Partner Details'
          and (e.user = %(user)s or e.email = %(user)s)
          and ifnull(e.status, 'Active') = 'Active'
        order by e.modified desc
        limit 1
        """,
        {'user': user},
        as_dict=True,
    )
    return frappe._dict(rows[0]) if rows else None


def find_survey_field_units(settlement, intervention_unit=None, survey=None):
    """Active Survey Field Units covering a settlement (and, when given, one
    of its intervention units). A unit with no intervention unit set covers
    the whole settlement, so it matches either way."""
    filters = {'settlement': settlement, 'status': 'Active'}
    if survey:
        filters['survey'] = survey
    units = frappe.get_all(
        'Survey Field Unit',
        filters=filters,
        fields=['name', 'survey', 'settlement_intervention_unit'],
        order_by='creation asc',
    )
    if intervention_unit:
        exact = [u for u in units if u.settlement_intervention_unit == intervention_unit]
        if exact:
            return exact
    return [u for u in units if not u.settlement_intervention_unit]


@frappe.whitelist()
def get_household_field_defaults():
    """What a new Household Profile can fill in for the logged-in user: their
    partner and worker record, and every place they're tagged to work (a
    settlement, or one of its intervention units, through the Settlement's
    Workers table) with the Survey Field Unit covering that place.
    Shape: { partner_organization, assigned_worker, assignments: [{ settlement,
    settlement_intervention_unit, survey_field_unit, survey }] } - empty for
    anyone who isn't a partner worker."""
    employee = get_user_employee()
    if not employee:
        return {}

    tagged = frappe.get_all(
        'Settlement Worker',
        filters={'worker': employee.name, 'parenttype': 'Settlement'},
        fields=['parent', 'intervention_unit'],
        order_by='creation asc',
    )
    assignments = []
    seen = set()
    for row in tagged:
        if not frappe.has_permission('Settlement', 'read', doc=row.parent):
            continue
        units = find_survey_field_units(row.parent, row.intervention_unit) or [None]
        for unit in units:
            key = (row.parent, row.intervention_unit, unit.name if unit else None)
            if key in seen:
                continue
            seen.add(key)
            assignments.append({
                'settlement': row.parent,
                'settlement_intervention_unit': row.intervention_unit,
                'survey_field_unit': unit.name if unit else None,
                'survey': unit.survey if unit else None,
            })
    return {
        'partner_organization': employee.parent,
        'assigned_worker': employee.name,
        'assignments': assignments,
    }


@frappe.whitelist()
def get_link_options(doctype, filters=None, limit=1000):
    """Records of `doctype` as [{ name, <title_field> }] for a Link dropdown.
    Exists for Links that point at a *child* table (a worker, an intervention
    unit): Frappe's list query silently drops every field except `name` for a
    child doctype unless it is told the parent doctype, so the generic
    document API can't return the titles those dropdowns need. A child row is
    offered if its parent is readable by the user."""
    if not frappe.db.exists('DocType', doctype):
        return []
    meta = frappe.get_meta(doctype)
    title_field = meta.title_field if meta.title_field else 'name'
    fields = ['name'] if title_field == 'name' else ['name', title_field]
    filters = frappe.parse_json(filters) or {}
    limit = min(int(limit), 1000)

    if meta.istable:
        rows = frappe.get_all(
            doctype, filters=filters, fields=[*fields, 'parenttype'], order_by='creation asc', limit_page_length=limit
        )
        readable = {}
        out = []
        for r in rows:
            pt = r.pop('parenttype', None)
            if pt not in readable:
                readable[pt] = bool(pt) and frappe.has_permission(pt, 'read')
            if readable[pt]:
                out.append(r)
        return out

    if not frappe.has_permission(doctype, 'read'):
        return []
    return frappe.get_list(doctype, filters=filters, fields=fields, limit_page_length=limit)


@frappe.whitelist()
def get_link_titles(doctype, names):
    """Titles (the title_field value) for a batch of records of `doctype`, so
    list cells, cards and child-table rows can show a person's name instead of
    their record ID. `names` is a JSON list. Returns { name: title } only for
    records the user may read and that actually have a title; the caller falls
    back to the ID for the rest."""
    names = frappe.parse_json(names) or []
    names = [n for n in names if isinstance(n, str)][:500]
    if not names or not frappe.db.exists('DocType', doctype):
        return {}

    meta = frappe.get_meta(doctype)
    title_field = meta.title_field
    if not title_field or title_field == 'name':
        return {}

    if meta.istable:
        # A child row is readable if its parent is.
        rows = frappe.get_all(
            doctype,
            filters={'name': ['in', names]},
            fields=['name', title_field, 'parenttype'],
        )
        rows = [r for r in rows if r.parenttype and frappe.has_permission(r.parenttype, 'read')]
    else:
        if not frappe.has_permission(doctype, 'read'):
            return {}
        rows = frappe.get_list(doctype, filters={'name': ['in', names]}, fields=['name', title_field])

    return {r['name']: r[title_field] for r in rows if r.get(title_field)}


@frappe.whitelist()
def get_field_function_registry():
    """The built-in field functions and what each accepts/produces, so the
    Field Function Mapping form (desk and Vue) can offer only field types a
    function can actually use. Shape: { "<Function>": { description,
    trigger_fieldtypes, input_fieldtypes?, outputs: { key: { label,
    fieldtypes } } } }"""
    if frappe.session.user == 'Guest':
        frappe.throw(_('Not permitted'), frappe.PermissionError)
    from janadhikara.field_functions import FIELD_FUNCTIONS

    return FIELD_FUNCTIONS


@frappe.whitelist()
def get_field_function_rules():
    """Return every enabled Field Function Mapping, so the Vue app knows which
    function to run when a field changes and where each output goes.
    Shape: [{ target_doctype, trigger_field, function_name,
              mappings: [{ output, target_field, input_field, only_if_empty }] }]"""
    if frappe.session.user == 'Guest':
        frappe.throw(_('Not permitted'), frappe.PermissionError)

    rules = []
    for name in frappe.get_all('Field Function Mapping', filters={'enabled': 1}, pluck='name'):
        doc = frappe.get_cached_doc('Field Function Mapping', name)
        rules.append({
            'target_doctype': doc.target_doctype,
            'trigger_field': doc.trigger_field,
            'function_name': doc.function_name,
            'mappings': [
                {
                    'output': row.output,
                    'target_field': row.target_field,
                    'input_field': row.input_field or None,
                    'only_if_empty': bool(row.only_if_empty),
                }
                for row in doc.field_mappings
            ],
        })
    return rules


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
        # The module's sidebar as an ordered list of Links, Section Breaks
        # (group headings that fold up when clicked) and
        # Spacers, where a Link can be a child (indented sub-item) of the Link
        # above it. `doctypes` is the same list narrowed to just the Links, for
        # everything that only needs "which doctypes does this module open".
        items = []
        for item in module_doc.doctypes or []:
            kind = item.item_type or 'Link'
            if kind == 'Link':
                if not item.doctype_name:
                    continue
                items.append({
                    'type': 'Link',
                    'doctype_name': item.doctype_name,
                    'label': item.label or item.doctype_name,
                    'icon': item.icon or module_doc.icon or 'file-text',
                    'route': item.route or frappe.scrub(item.doctype_name).replace('_', '-'),
                    'child': bool(item.child),
                })
            elif kind == 'Section Break':
                items.append({
                    'type': 'Section Break',
                    'label': item.label,
                    'icon': item.icon or None,
                    # Every group folds up when its heading is clicked, and starts open.
                    'collapsible': True,
                    'keep_closed': False,
                })
            else:
                items.append({'type': 'Spacer'})
        doctypes = [i for i in items if i['type'] == 'Link']
        if not doctypes:
            continue
        modules.append({
            'label': module_doc.label,
            'icon': module_doc.icon or 'file-text',
            'items': items,
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

