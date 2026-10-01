# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from janadhikara.field_functions import FIELD_FUNCTIONS, all_output_keys


class TestFieldFunctionMapping(IntegrationTestCase):
	def test_select_options_match_registry(self):
		"""The Select options in the doctype JSON must list every registered
		function and output - add to both when registering a new function."""
		function_opts = [o for o in frappe.get_meta("Field Function Mapping").get_field("function_name").options.split("\n") if o]
		output_opts = [o for o in frappe.get_meta("Field Function Mapping Item").get_field("output").options.split("\n") if o]
		self.assertEqual(function_opts, list(FIELD_FUNCTIONS))
		self.assertEqual(output_opts, all_output_keys())
