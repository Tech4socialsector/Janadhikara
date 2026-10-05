"""IDs are never typed in: a record's name comes from a series, and the
matching code field (Household ID, Settlement Code, ...) is filled with it."""

from frappe.model.naming import make_autoname


def autoname_with_code(doc, prefix, code_fieldname):
	"""Controller `autoname`: name the record `<prefix>-00001` and copy it into the code field."""
	doc.name = make_autoname(f"{prefix}-.#####", doc.doctype)
	doc.set(code_fieldname, doc.name)
