# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from janadhikara.city_directory import get_city

# Choosing a provider preset fills in its address (and, for OpenRouter, the model this app is set up for).
# The request itself always uses the Base URL and Model fields, so any other OpenAI-compatible endpoint
# still works with "Custom".
PRESETS = {
	"OpenRouter": {"base_url": "https://openrouter.ai/api/v1", "model": "google/gemini-3.1-flash-lite"},
}


class AppSetting(Document):
	def validate(self):
		self.fill_city_details()
		self.drop_key_of_previous_provider()
		preset = PRESETS.get(self.ai_provider)
		if not preset:
			return
		if self.has_value_changed("ai_provider") or not self.ai_api_base_url:
			self.ai_api_base_url = preset["base_url"]
			if not self.ai_model or self.has_value_changed("ai_provider"):
				self.ai_model = preset["model"]

	def on_update(self):
		"""A city brings its own doctypes (city_packs/<city code>.json): the site follows the city chosen."""
		old = self.get_doc_before_save()
		if not old or old.city_code != self.city_code:
			from janadhikara.city_pack import sync_city_packs

			sync_city_packs()

	def fill_city_details(self):
		"""The city is normally chosen once (only a System Manager can change it later); its code, state and map view come from the city directory."""
		old = self.get_doc_before_save()
		if old and old.city_code and old.city_name != self.city_name and "System Manager" not in frappe.get_roles():
			frappe.throw(_("The city of this site is set to {0}; only a System Manager can change it.").format(old.city_name))
		city = get_city(self.city_name)
		if not city:
			return
		self.city_code, self.state = city["code"], city["state"]
		self.map_center_lat, self.map_center_lng = city["map_center"]
		self.map_default_zoom = city["map_zoom"]
		(self.map_south, self.map_west), (self.map_north, self.map_east) = city["map_bounds"]

	def drop_key_of_previous_provider(self):
		"""An API key belongs to one provider: when the address changes without a new key being typed,
		the saved key is removed so it is never sent to a different company."""
		old = self.get_doc_before_save()
		if not old or old.ai_api_base_url == self.ai_api_base_url and old.ai_provider == self.ai_provider:
			return
		new_key_typed = bool(self.ai_api_key) and set(str(self.ai_api_key)) != {"*"}
		if not new_key_typed:
			frappe.db.delete("__Auth", {"doctype": "App Setting", "name": "App Setting", "fieldname": "ai_api_key"})
			self.ai_api_key = ""
