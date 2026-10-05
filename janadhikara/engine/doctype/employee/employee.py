# Copyright (c) 2026, tech4socialsector@azimpremjifoundation.org and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from janadhikara.naming import autoname_with_code


class Employee(Document):
	def autoname(self):
		autoname_with_code(self, "EMP", "worker_code")
