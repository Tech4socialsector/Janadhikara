"""What may leave the server for the external language model.

The model gets record IDs, counts and answers - never a person's name, phone number, address, position or
date of birth. Where the user asks for such a detail, the tool result carries a placeholder and the app puts
the real value into the reply after the model has answered (see data_service.rehydrate), checked against the
signed-in user's own permissions.

The assistant's answers come from a model run by another company, so nothing that identifies a person
or a household may be sent to it. Three layers:
  1. data_service never returns fields in PERSONAL_FIELDNAMES (phone, e-mail, address, position, date of birth), or Phone / Email / Geolocation fields,
     whatever an AI Data Policy says.
  2. scrub() removes anything that still looks like a phone number, e-mail address, Aadhaar or PAN
     number, GPS position or file link from every text sent to the model (the user's own typing, the
     conversation history and the tool results).
  3. Requests ask the provider to route only to endpoints that do not store or train on the data.
"""

import re

# People's names: the model refers to people by record ID only.
NAME_FIELDNAMES = {
	"member_name", "respondent_name", "household_head_name", "orw_name", "worker_name", "employee_name",
	"contact_person", "full_name", "first_name", "last_name",
}
# Everything that identifies, locates or contacts a person. The model never sees these values: it gets a
# placeholder (see token()) that the app replaces with the real value, for the signed-in user only, in the reply.
PERSONAL_FIELDNAMES = NAME_FIELDNAMES | {
	"mobile_number", "contact_number", "phone", "email", "address", "house_no", "street_name", "latitude",
	"longitude", "geo_location", "date_of_birth", "dob", "udid_number", "consent_taken_by", "user",
}
PERSONAL_OPTIONS = {"Phone", "Email", "URL"}
PERSONAL_FIELDTYPES = {"Geolocation", "Phone"}

_PATTERNS = (
	(re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
	(re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[id number]"),
	(re.compile(r"(?<!\d)(?:\+?91[\s-]?)?\d{5}[\s-]?\d{5}(?!\d)"), "[phone]"),
	(re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"), "[id number]"),
	(re.compile(r"(?<!\d)-?\d{1,3}\.\d{4,}(?!\d)"), "[location]"),
	(re.compile(r"/(?:private/)?files/\S+"), "[file]"),
)


def scrub_text(text):
	for pattern, replacement in _PATTERNS:
		text = pattern.sub(replacement, text)
	return text


def scrub(value):
	"""scrub_text applied to every string inside a message, a tool result, or any nested list/dict."""
	if isinstance(value, str):
		return scrub_text(value)
	if isinstance(value, dict):
		return {key: scrub(item) for key, item in value.items()}
	if isinstance(value, (list, tuple)):
		return [scrub(item) for item in value]
	return value


def is_personal_field(df):
	return (
		df.fieldname in PERSONAL_FIELDNAMES
		or df.fieldtype in PERSONAL_FIELDTYPES
		or (df.fieldtype == "Data" and (df.options or "") in PERSONAL_OPTIONS)
	)


# A placeholder for one personal value: [[Doctype|RECORD-ID|fieldname]]
TOKEN_RE = re.compile(r"\[\[([^|\[\]]{1,80})\|([^|\[\]]{1,140})\|([a-z0-9_]{1,64})\]\]")


def token(doctype, name, fieldname):
	return f"[[{doctype}|{name}|{fieldname}]]"
