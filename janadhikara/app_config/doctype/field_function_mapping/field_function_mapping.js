// Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
// For license information, please see license.txt

// Field-name dropdowns driven by the chosen Target Doctype: Trigger Field,
// and (in the Output Mapping grid) Target Field and Also Uses Field, list the
// real fields of that doctype so nothing has to be typed from memory. Trigger
// and Also Uses are narrowed to the field types the chosen function accepts.
// (The Vue app does the same - see DoctypeFieldPicker.vue.)

const LAYOUT_TYPES = ["Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button", "Image"];

function field_options(doctype, allowed_types) {
	return frappe
		.get_meta(doctype)
		.fields.filter((df) => !LAYOUT_TYPES.includes(df.fieldtype) && !df.hidden)
		.filter((df) => !allowed_types || allowed_types.includes(df.fieldtype))
		.map((df) => ({
			label: `${df.label || df.fieldname}  (${df.fieldname} · ${df.fieldtype})`,
			value: df.fieldname,
		}));
}

function load_registry() {
	if (!frappe.field_function_registry) {
		frappe.field_function_registry = frappe
			.xcall("janadhikara.api.get_field_function_registry")
			.catch(() => ({}));
	}
	return frappe.field_function_registry;
}

async function refresh_field_dropdowns(frm) {
	const doctype = frm.doc.target_doctype;
	const grid = frm.fields_dict.field_mappings && frm.fields_dict.field_mappings.grid;

	if (!doctype) {
		frm.set_df_property("trigger_field", "options", []);
		if (grid) {
			grid.update_docfield_property("target_field", "options", []);
			grid.update_docfield_property("input_field", "options", []);
		}
		return;
	}

	await new Promise((resolve) => frappe.model.with_doctype(doctype, resolve));
	const registry = await load_registry();
	const func = registry[frm.doc.function_name] || {};

	frm.set_df_property("trigger_field", "options", field_options(doctype, func.trigger_fieldtypes));
	if (grid) {
		grid.update_docfield_property("target_field", "options", field_options(doctype));
		grid.update_docfield_property("input_field", "options", field_options(doctype, func.input_fieldtypes));
	}
	frm.refresh_field("trigger_field");
}

frappe.ui.form.on("Field Function Mapping", {
	refresh(frm) {
		refresh_field_dropdowns(frm);
	},
	target_doctype(frm) {
		// The old picks belong to the previous doctype - clear them.
		frm.set_value("trigger_field", "");
		(frm.doc.field_mappings || []).forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, "target_field", "");
			frappe.model.set_value(row.doctype, row.name, "input_field", "");
		});
		refresh_field_dropdowns(frm);
	},
	function_name(frm) {
		refresh_field_dropdowns(frm);
	},
});
