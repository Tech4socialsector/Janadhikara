import frappe

# Record IDs run in sequence without a hyphen (SET0001, HH0001, IND0001, HOU0001),
# and the new Assam District and Welfare Board masters get their values.
PREFIXES = {"Settlement": "SET", "Household Profile": "HH", "Individual Profile": "IND"}
CODE_FIELDS = {"Household Profile": "hhid", "Individual Profile": "individual_id"}

DISTRICTS = (
	"Baksa Bajali Barpeta Biswanath Bongaigaon Cachar Charaideo Chirang Darrang Dhemaji Dhubri Dibrugarh Goalpara Golaghat "
	"Hailakandi Hojai Jorhat Kamrup Karbi_Anglong Karimganj Kokrajhar Lakhimpur Majuli Morigaon Nagaon Nalbari Sivasagar "
	"Sonitpur South_Salmara-Mankachar Tamulpur Tinsukia Udalguri West_Karbi_Anglong Dima_Hasao Kamrup_Metropolitan"
).split()
BOARDS = (
	"Assam_Board_of_WAKF|Assam_Minorities_Development_Board|Assam_Building_and_Other_Construction_Workers_Welfare_Board_(ABOCWWB)|"
	"Assam_State_Disability_Welfare_Board|Assam_State_Housing_Board|Transgender_Welfare_Board,_Assam|Urban_Water_Supply_&_Sewerage_Board_Assam|"
	"State_Haj_Committee|Christian_Welfare_Board|Buddhist_Welfare_Board|Sikh_Welfare_Board|Others"
).split("|")


def _seed(doctype, field, values):
	for value in values:
		value = value.replace("_", " ")
		if not frappe.db.exists(doctype, value):
			frappe.get_doc({"doctype": doctype, field: value, "enabled": 1}).insert(ignore_permissions=True)


def _renumber(doctype, prefix):
	for index, name in enumerate(frappe.get_all(doctype, order_by="creation asc, name asc", pluck="name"), start=1):
		new = f"{prefix}{index:04d}"
		if name != new:
			frappe.rename_doc(doctype, name, new, force=True)
		code = CODE_FIELDS.get(doctype)
		if code:
			frappe.db.set_value(doctype, new, code, new, update_modified=False)
		if doctype == "Household Profile":
			house_id = frappe.db.get_value(doctype, new, "house_id")
			if house_id:
				frappe.db.set_value(doctype, new, "house_id", f"HOU{index:04d}", update_modified=False)
	return frappe.db.count(doctype)


def _set_series(key, current):
	frappe.db.sql("delete from `tabSeries` where name in (%s, %s)", (key, f"{key}-"))
	frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (key, current))


def execute():
	_seed("Assam District", "district_name", DISTRICTS)
	_seed("Welfare Board", "board_name", BOARDS)
	for doctype, prefix in PREFIXES.items():
		_set_series(prefix, _renumber(doctype, prefix))
	_set_series("HOU", frappe.db.count("Household Profile", {"house_id": ["is", "set"]}))
	frappe.db.commit()
