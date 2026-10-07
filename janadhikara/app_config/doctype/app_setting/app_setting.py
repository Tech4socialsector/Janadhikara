# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Choosing a provider preset fills in its address (and, for OpenRouter, the model this app is set up for).
# The request itself always uses the Base URL and Model fields, so any other OpenAI-compatible endpoint
# still works with "Custom".
PRESETS = {
	"OpenRouter": {"base_url": "https://openrouter.ai/api/v1", "model": "google/gemini-3.1-flash-lite"},
}


class AppSetting(Document):
	def validate(self):
		self.drop_key_of_previous_provider()
		preset = PRESETS.get(self.ai_provider)
		if not preset:
			return
		if self.has_value_changed("ai_provider") or not self.ai_api_base_url:
			self.ai_api_base_url = preset["base_url"]
			if not self.ai_model or self.has_value_changed("ai_provider"):
				self.ai_model = preset["model"]

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
