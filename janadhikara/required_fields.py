"""Mandatory questions that an administrator can change from the cloud site.

Customize Form can make an optional field mandatory but never the other way (a field that is mandatory in the app's code
stays mandatory). So these fields are optional in the doctype files and made mandatory here, as Property Setters: the
very thing Customize Form edits. An administrator can then tick or untick Mandatory on a field in Customize Form like any
other setting, and a later deploy does not put it back.

Each field is made mandatory once. The ones already done are remembered, so a field that was relaxed on a site stays
relaxed. To add a mandatory field, add it to REQUIRED below (not "reqd" in the doctype file).
"""
import json

import frappe

REQUIRED = {
 "Education Record": [
  "education_level",
  "status"
 ],
 "Entitlement": [
  "scheme_name",
  "entitlement_type",
  "status"
 ],
 "Health Condition": [
  "condition",
  "condition_type"
 ],
 "Household Profile": [
  "household_status",
  "validation_status",
  "settlement",
  "partner_organization",
  "record_date"
 ],
 "Individual Document": [
  "document_type"
 ],
 "Individual Profile": [
  "record_date",
  "household",
  "member_name",
  "validation_status"
 ],
 "Settlement": [
  "record_date",
  "settlement_name",
  "cluster",
  "validation_status"
 ],
 "Settlement Street Photo": [
  "photo"
 ],
 "Employee": [
  "worker_name",
  "role",
  "status",
  "email"
 ],
 "Partner Details": [
  "organization_name",
  "organization_type",
  "status",
  "contact_person",
  "state",
  "district"
 ],
 "Household Cooking Fuel": [
  "fuel"
 ]
}

SEEDED_KEY = "janadhikara_required_seeded"


def seed_required_fields():
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	seeded = set(json.loads(frappe.db.get_default(SEEDED_KEY) or "[]"))
	done = False
	for doctype, fieldnames in REQUIRED.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		for fieldname in fieldnames:
			key = f"{doctype}:{fieldname}"
			if key in seeded or not meta.has_field(fieldname):
				continue
			if not frappe.db.exists("Property Setter", {"doc_type": doctype, "field_name": fieldname, "property": "reqd"}):
				make_property_setter(doctype, fieldname, "reqd", 1, "Check", validate_fields_for_doctype=False)
			seeded.add(key)
			done = True
	if done:
		frappe.db.set_default(SEEDED_KEY, json.dumps(sorted(seeded)))
		frappe.db.commit()
		for doctype in REQUIRED:
			frappe.clear_cache(doctype=doctype)
