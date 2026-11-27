"""Give the photos in a record's photo table a readable file name: <record ID>-<day><month>, e.g. SET0013-19Nov.jpg
(a second photo that day SET0013-19Nov-2.jpg)."""

import os
import re
import shutil
from urllib.parse import unquote

import frappe
from frappe.utils import getdate, nowdate


def name_table_photos(doc, table_field, photo_field="photo"):
	"""Rename each row's photo to <doc.name>-<day><month><ext>. Called after save, so the record has its final ID, also for
	one made on the phone offline. A photo already named this way (on any day) is left as is."""
	for row in doc.get(table_field) or []:
		url = row.get(photo_field)
		if not url or not url.startswith(("/files/", "/private/files/")):
			continue  # empty, or a link to an image elsewhere

		old_name = unquote(url.rsplit("/", 1)[-1])
		ext = os.path.splitext(old_name)[1].lower() or ".jpg"
		# already named (on any day, e.g. SET0013-19Nov.jpg or SET0013-19Nov-2.jpg): keep it
		if re.fullmatch(re.escape(f"{doc.name}-") + r"\d{2}[A-Z][a-z]{2}(-\d+)?" + re.escape(ext), old_name):
			continue
		base = f"{doc.name}-{getdate(nowdate()).strftime('%d%b')}"

		is_private = url.startswith("/private/")
		folder = frappe.get_site_path("private" if is_private else "public", "files")
		old_path = os.path.join(folder, old_name)
		if not os.path.isfile(old_path):
			continue

		new_name, n = f"{base}{ext}", 1
		while os.path.exists(os.path.join(folder, new_name)):
			n += 1
			new_name = f"{base}-{n}{ext}"
		shutil.copy2(old_path, os.path.join(folder, new_name))
		new_url = ("/private/files/" if is_private else "/files/") + new_name

		# The File record(s) of this upload move to the new name. The same picture may also be used elsewhere
		# (Frappe reuses a stored file when the same content is uploaded again): those keep the old file.
		files = frappe.get_all("File", filters={"file_url": url}, fields=["name", "attached_to_name"])
		mine = [f.name for f in files if f.attached_to_name in (None, "", doc.name, row.name)]
		for name in mine:
			frappe.db.set_value(
				"File",
				name,
				{"file_name": new_name, "file_url": new_url, "attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
				update_modified=False,
			)
		if not mine:
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": new_name,
					"file_url": new_url,
					"is_private": is_private,
					"attached_to_doctype": doc.doctype,
					"attached_to_name": doc.name,
				}
			).insert(ignore_permissions=True)

		frappe.db.set_value(row.doctype, row.name, photo_field, new_url, update_modified=False)
		row.set(photo_field, new_url)

		# the old file goes only once the save is committed, and only when nothing else still uses it
		if len(mine) == len(files):
			frappe.db.after_commit.add(lambda p=old_path: os.path.isfile(p) and os.remove(p))


# ---- Photos taken with no connection ------------------------------------------------------------
# With no connection a photo can't be uploaded: the phone keeps it inside the saved record as a data URL
# (data:image/jpeg;base64,...) - encrypted there with the rest of the record. When the record reaches the
# server (synced, or saved once the connection is back) every such photo becomes a File here, before the
# record is checked and saved, so only a normal file link is ever stored.
DATA_URL = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,(.+)$", re.S)
MAX_PHOTO_BYTES = 15 * 1024 * 1024
PUBLIC_UPLOAD_DOCTYPES = ("App Setting", "Partner Details", "User")


def save_photos_from_device(doc, method=None):
	"""doc_events "*" before_validate: turn photos kept on the phone (data URLs) into stored files."""
	if not isinstance(doc, frappe.model.document.Document):
		return
	rows = [doc]
	for df in doc.meta.get_table_fields():
		rows.extend(doc.get(df.fieldname) or [])
	for row in rows:
		for df in row.meta.fields:
			if df.fieldtype not in ("Attach Image", "Attach"):
				continue
			value = row.get(df.fieldname)
			if isinstance(value, str) and value.startswith("data:"):
				row.set(df.fieldname, _store_data_url(doc, value))


def _store_data_url(doc, value):
	import base64

	match = DATA_URL.match(value)
	if not match:
		frappe.throw(frappe._("This photo could not be read. Take it again."))
	try:
		content = base64.b64decode(match.group(2), validate=False)
	except Exception:
		frappe.throw(frappe._("This photo could not be read. Take it again."))
	if len(content) > MAX_PHOTO_BYTES:
		frappe.throw(frappe._("A photo is too large. Take it again."))
	ext = {"jpeg": ".jpg", "jpg": ".jpg"}.get(match.group(1), f".{match.group(1)}")
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{doc.name}-{getdate(nowdate()).strftime('%d%b')}{ext}",
			"content": content,
			"is_private": 0 if doc.doctype in PUBLIC_UPLOAD_DOCTYPES else 1,
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
		}
	).insert(ignore_permissions=True)
	return file.file_url
