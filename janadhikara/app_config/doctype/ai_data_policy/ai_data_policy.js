// Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
// For license information, please see license.txt

// Field Rules > Field: a dropdown of the chosen doctype's real fields.
const LAYOUT_TYPES = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button", "Image"];

async function refresh_field_options(frm) {
	const grid = frm.fields_dict.field_rules && frm.fields_dict.field_rules.grid;
	if (!grid) return;
	if (!frm.doc.target_doctype) {
		grid.update_docfield_property("policy_field", "options", []);
		return;
	}
	await new Promise((resolve) => frappe.model.with_doctype(frm.doc.target_doctype, resolve));
	const options = frappe
		.get_meta(frm.doc.target_doctype)
		.fields.filter((df) => !LAYOUT_TYPES.includes(df.fieldtype))
		.map((df) => ({ label: `${df.label || df.fieldname}  (${df.fieldname} \u00b7 ${df.fieldtype})`, value: df.fieldname }));
	grid.update_docfield_property("policy_field", "options", options);
}

frappe.ui.form.on("AI Data Policy", {
	refresh: refresh_field_options,
	target_doctype: refresh_field_options,
});
