"""AI Data Policy lifecycle: seeds for the doctypes that exist today, and the
guarantee that every doctype added later starts invisible to the assistant.

Rule for this codebase: whenever a doctype is created, it gets an AI Data
Policy. `ensure_policies` (run after every migrate) and `on_doctype_created`
(run when a DocType is inserted) create one automatically - *disabled*, so a
new doctype is off-limits to the assistant until a System Manager reviews it,
decides what the assistant may do, and lists its confidential fields. To make
a doctype available from the start, add it to SEED below (and write a patch
that seeds it - see patches/v1_1/seed_ai_data_policies.py).
"""

import frappe

from janadhikara.ai.data_service import ALWAYS_BLOCKED, POLICY_CACHE_KEY

APP_MODULES = ('Masters', 'Common', 'App Config', 'Engine', 'Baseline')

# doctype -> what the assistant may do, and its confidential / protected fields.
# `hidden`: never seen, filtered on or set. `read_only`: seen, never set.
SEED = {
    'Household Profile': {
        'can_write': 1,
        'hidden': {
            'address': 'home address', 'landmark': 'home location', 'latitude': 'home location',
            'longitude': 'home location', 'geo_location': 'home location', 'contact_number': 'contact number',
            'question_answers': 'questionnaire answers',
        },
        'read_only': {
            'assigned_worker': 'set from the signed-in user',
            'validation_status': 'set by validators', 'validation_comments': 'set by validators',
        },
    },
    'Individual Profile': {
        'hidden': {
            'date_of_birth': 'personal detail', 'age': 'personal detail', 'mobile_number': 'contact number',
            'monthly_income': 'income', 'health_conditions': 'health information',
            'entitlements': 'entitlement details (consent-based)', 'documents': 'identity documents (consent-based)',
            'consent_purpose': 'consent record',
        },
        'read_only': {
            'surveyor': 'set from the signed-in user', 'surveyor_name': 'set from the signed-in user',
            'consent_given': 'recorded with the person, not by the assistant', 'consent_mode': 'consent record',
            'consent_date': 'consent record', 'consent_taken_by': 'consent record',
            'consent_withdrawn_on': 'consent record',
        },
    },
    'Settlement': {
        'can_write': 1,
        'hidden': {
            'latitude': 'location', 'longitude': 'location', 'geo_location': 'location',
            'settlement_boundary': 'boundary geometry',
        },
        'read_only': {
            'partner_organization': 'controls which workers can be tagged', 'boundary_area': 'computed from the map',
            'boundary_perimeter': 'computed from the map', 'boundary_captured_by': 'set by the system',
            'boundary_captured_on': 'set by the system',
        },
    },
    'Settlement Intervention Unit': {
        'hidden': {
            'latitude': 'location', 'longitude': 'location', 'geo_location': 'location', 'boundary': 'boundary geometry',
        },
    },
    'Settlement Worker': {},
    'Partner Details': {
        'hidden': {
            'contact_person': 'personal contact', 'contact_number': 'contact number', 'email': 'email address',
            'address': 'address', 'partner_logo': 'file',
        },
    },
    'Employee': {
        'hidden': {'mobile_number': 'contact number', 'email': 'email address', 'user': 'login account'},
    },
    'Survey': {},
    'Relationship Type': {},
    'Announcement': {},
}


def _rules(policy_fields):
    return [
        {'policy_field': field, 'handling': handling, 'reason': reason}
        for handling, mapping in policy_fields
        for field, reason in mapping.items()
    ]


def seed_policies():
    """Create the policies above for doctypes that don't have one yet. Never
    touches an existing policy, so an admin's edits survive."""
    created = []
    for doctype, spec in SEED.items():
        if frappe.db.exists('AI Data Policy', doctype) or not frappe.db.exists('DocType', doctype):
            continue
        frappe.get_doc({
            'doctype': 'AI Data Policy',
            'target_doctype': doctype,
            'enabled': 1,
            'can_read': 1,
            'can_write': spec.get('can_write', 0),
            'include_child_tables': 1,
            'max_rows': 20,
            'description': 'Seeded default - review before widening.',
            'field_rules': _rules([('Hidden', spec.get('hidden', {})), ('Read Only', spec.get('read_only', {}))]),
        }).insert(ignore_permissions=True)
        created.append(doctype)
    if created:
        frappe.cache().delete_value(POLICY_CACHE_KEY)
    return created


def _create_disabled_policy(doctype):
    if doctype in ALWAYS_BLOCKED or frappe.db.exists('AI Data Policy', doctype):
        return False
    frappe.get_doc({
        'doctype': 'AI Data Policy',
        'target_doctype': doctype,
        'enabled': 0,
        'can_read': 1,
        'can_write': 0,
        'include_child_tables': 1,
        'max_rows': 20,
        'description': 'Created automatically with the doctype. The assistant cannot see it until a System Manager reviews it and turns it on.',
    }).insert(ignore_permissions=True)
    return True


def ensure_policies():
    """after_migrate: every doctype in this app's modules has a policy - new
    ones get a disabled one. Idempotent."""
    if not frappe.db.exists('DocType', 'AI Data Policy'):
        return
    for doctype in frappe.get_all('DocType', filters={'module': ['in', APP_MODULES], 'issingle': 0}, pluck='name'):
        _create_disabled_policy(doctype)
    frappe.cache().delete_value(POLICY_CACHE_KEY)


def on_doctype_created(doc, method=None):
    """DocType after_insert: a doctype created in one of this app's modules
    (e.g. through the desk's DocType editor) gets its disabled policy at once,
    without waiting for the next migrate."""
    if doc.module in APP_MODULES and not doc.issingle and frappe.db.exists('DocType', 'AI Data Policy'):
        _create_disabled_policy(doc.name)
