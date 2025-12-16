# Copyright (c) 2025, abdopcnet@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt


def execute(filters=None):
	"""
	Execute function for Sales Commission Report (تقرير عمولة مناديب البيع)
	
	Args:
		filters (dict): Dictionary containing filter values
		
	Returns:
		tuple: (columns, data) - columns definition and data rows
	"""
	if not filters:
		filters = frappe._dict({})
	
	# Get columns definition
	columns = get_columns()
	
	# Get data based on filters
	data = get_data(filters)
	
	return columns, data


def get_columns():
	"""Define report columns"""
	columns = [
		{
			"fieldname": "sales_invoice",
			"label": _("رقم الفاتورة"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
		},
		{
			"fieldname": "company",
			"label": _("الشركة"),
			"fieldtype": "Link",
			"options": "Company",
		},
		{
			"fieldname": "customer",
			"label": _("العميل"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"fieldname": "posting_date",
			"label": _("تاريخ الإثبات"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "customer_invoice_reference_no",
			"label": _("رقم الفاتورة المخصص"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "grand_total",
			"label": _("الإجمالي"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "subtotal_without_vat",
			"label": _("المجموع الفرعي بدون ضريبة"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "sales_person",
			"label": _("مندوب المبيعات"),
			"fieldtype": "Link",
			"options": "Sales Person",
		},
		{
			"fieldname": "commission_rate",
			"label": _("نسبة العمولة (%)"),
			"fieldtype": "Percent",
		},
		{
			"fieldname": "mode_of_payment",
			"label": _("طريقة الدفع"),
			"fieldtype": "Link",
			"options": "Mode of Payment",
		},
		{
			"fieldname": "paid_amount",
			"label": _("المبلغ المدفوع"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "total_allocated_amount",
			"label": _("إجمالي المبلغ المخصص"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "custom_total_taxes",
			"label": _("إجمالي الاستقطاعات"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "custom_total_cheques_amount",
			"label": _("إجمالي مبلغ الشيكات"),
			"fieldtype": "Currency",
		},
		{
			"fieldname": "reference_date",
			"label": _("تاريخ المرجع"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "reference_no",
			"label": _("رقم المرجع"),
			"fieldtype": "Data",
		}
	]
	
	return columns


def get_data(filters):
	"""
	Get report data based on filters
	
	Args:
		filters (dict): Filter dictionary containing from_date, to_date, etc.
		
	Returns:
		list: List of dictionaries containing report data
	"""
	# Query: One row per invoice with aggregated payment data
	query = """
		SELECT
			si.name AS sales_invoice,
			si.company,
			si.customer,
			si.posting_date,
			si.custom_sales_invoice_number AS customer_invoice_reference_no,
			si.grand_total,
			(si.grand_total - COALESCE(si.total_taxes_and_charges, 0)) AS subtotal_without_vat,
			(SELECT sales_person FROM `tabSales Team` 
			 WHERE parent = si.name AND parenttype = 'Sales Invoice' 
			 LIMIT 1) AS sales_person,
			(SELECT commission_rate FROM `tabSales Team` 
			 WHERE parent = si.name AND parenttype = 'Sales Invoice' 
			 LIMIT 1) AS commission_rate,
			GROUP_CONCAT(DISTINCT pe.mode_of_payment SEPARATOR ', ') AS mode_of_payment,
			SUM(COALESCE(pe.paid_amount, 0)) AS paid_amount,
			SUM(COALESCE(per.allocated_amount, 0)) AS total_allocated_amount,
			SUM(COALESCE(pe.custom_total_taxes, 0)) AS custom_total_taxes,
			SUM(COALESCE(pe.custom_total_cheques_amount, 0)) AS custom_total_cheques_amount,
			GROUP_CONCAT(DISTINCT pe.reference_date SEPARATOR ', ') AS reference_date,
			GROUP_CONCAT(DISTINCT pe.reference_no SEPARATOR ', ') AS reference_no
		FROM `tabSales Invoice` si
		LEFT JOIN `tabPayment Entry Reference` per
			ON per.reference_doctype = 'Sales Invoice'
			AND per.reference_name = si.name
		LEFT JOIN `tabPayment Entry` pe
			ON pe.name = per.parent
			AND pe.docstatus = 1
			AND pe.party_type = 'Customer'
			AND pe.company = si.company
		WHERE si.docstatus = 1
	"""
	
	# Get conditions and parameters
	conditions, params = get_conditions(filters)
	
	if conditions:
		query += " AND " + conditions
	
	query += """
		GROUP BY si.name, si.company, si.customer, si.posting_date, 
		         si.custom_sales_invoice_number, si.grand_total, si.total_taxes_and_charges
		ORDER BY si.posting_date DESC, si.name DESC
	"""
	
	# Execute query
	if params:
		data = frappe.db.sql(query, params, as_dict=True)
	else:
		data = frappe.db.sql(query, as_dict=True)
	
	# Format numeric fields
	for row in data:
		row["grand_total"] = flt(row.get("grand_total", 0))
		row["subtotal_without_vat"] = flt(row.get("subtotal_without_vat", 0))
		row["commission_rate"] = flt(row.get("commission_rate", 0))
		row["paid_amount"] = flt(row.get("paid_amount", 0))
		row["total_allocated_amount"] = flt(row.get("total_allocated_amount", 0))
		row["custom_total_taxes"] = flt(row.get("custom_total_taxes", 0))
		row["custom_total_cheques_amount"] = flt(row.get("custom_total_cheques_amount", 0))
	
	return data


def get_conditions(filters):
	"""
	Build WHERE conditions based on filters with proper parameterization
	
	Args:
		filters (dict): Filter dictionary
		
	Returns:
		tuple: (conditions_string, params_dict) - SQL WHERE conditions and parameters
	"""
	conditions = []
	params = {}
	
	if filters.get("from_date"):
		from_date = getdate(filters.get("from_date"))
		conditions.append("si.posting_date >= %(from_date)s")
		params["from_date"] = from_date
	
	if filters.get("to_date"):
		to_date = getdate(filters.get("to_date"))
		conditions.append("si.posting_date <= %(to_date)s")
		params["to_date"] = to_date
	
	if filters.get("company"):
		conditions.append("si.company = %(company)s")
		params["company"] = filters.get("company")
	
	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		params["customer"] = filters.get("customer")
	
	if filters.get("sales_person"):
		conditions.append("sp.sales_person = %(sales_person)s")
		params["sales_person"] = filters.get("sales_person")
	
	if conditions:
		return " AND ".join(conditions), params
	
	return "", {}
