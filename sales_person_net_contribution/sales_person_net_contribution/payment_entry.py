"""
Payment Entry Script
Calculate net paid amount after deductions and update Sales Invoice Sales Team
"""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def calculate_net_contribution(payment_entry_name):
    """
    Calculate net paid after all deductions and update Sales Invoice Sales Team

    Args:
            payment_entry_name: Name of the Payment Entry document

    Returns:
            dict: Result message and calculated values
    """
    try:
        # Get Payment Entry document
        payment_entry = frappe.get_doc("Payment Entry", payment_entry_name)

        # Validate payment entry exists
        if not payment_entry:
            frappe.throw(_("Payment Entry not found"))

        # Read references child table
        # Check for Sales Invoice or Sales Order
        # Collect all invoice/order names to verify they are all the same
        sales_invoice_names = []
        sales_order_names = []

        for reference in payment_entry.references:
            if reference.reference_doctype == "Sales Invoice" and reference.reference_name:
                sales_invoice_names.append(reference.reference_name)
            elif reference.reference_doctype == "Sales Order" and reference.reference_name:
                sales_order_names.append(reference.reference_name)

        # Check if all Sales Invoices are the same (even if repeated in multiple rows)
        sales_invoice_name = None
        if sales_invoice_names:
            unique_invoices = set(sales_invoice_names)
            if len(unique_invoices) > 1:
                frappe.throw(
                    _("Multiple different Sales Invoices found. Please ensure only one invoice is referenced in all rows."))
            sales_invoice_name = sales_invoice_names[0]

        # Check if all Sales Orders are the same (even if repeated in multiple rows)
        sales_order_name = None
        if sales_order_names:
            unique_orders = set(sales_order_names)
            if len(unique_orders) > 1:
                frappe.throw(
                    _("Multiple different Sales Orders found. Please ensure only one order is referenced in all rows."))
            sales_order_name = sales_order_names[0]

        # Use Sales Invoice if available, otherwise use Sales Order
        invoice_name = sales_invoice_name or sales_order_name

        if not invoice_name:
            frappe.throw(
                _("No Sales Invoice or Sales Order found in references"))

        # Read deductions child table
        # Sum all amount values
        total_deductions = 0
        if payment_entry.deductions:
            for deduction in payment_entry.deductions:
                if deduction.amount:
                    try:
                        total_deductions += float(deduction.amount)
                    except (ValueError, TypeError):
                        pass

        # Get total paid amount
        # Convert to float to handle string values from database
        try:
            total_paid = float(payment_entry.total_allocated_amount or 0)
        except (ValueError, TypeError):
            total_paid = 0

        # Calculate net_paid
        net_paid = total_paid - total_deductions

        # Get Sales Invoice document
        if sales_invoice_name:
            sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
        else:
            # If Sales Order, we need to get the related Sales Invoice
            # For now, we'll work with Sales Invoice only
            frappe.throw(
                _("Sales Order support will be added later. Please use Sales Invoice."))

        # Get total taxes and charges from Sales Invoice
        # Convert to float to handle string values from database
        try:
            total_taxes_and_charges = float(
                sales_invoice.total_taxes_and_charges or 0)
        except (ValueError, TypeError):
            total_taxes_and_charges = 0

        # Get grand total from Sales Invoice
        try:
            grand_total = float(sales_invoice.grand_total or 0)
        except (ValueError, TypeError):
            grand_total = 0

        # Get currency from Payment Entry or Sales Invoice
        currency = payment_entry.paid_to_account_currency or payment_entry.company_currency or sales_invoice.currency or "ج.م"

        # Calculate net_paid_after_all_deductions
        net_paid_after_all_deductions = total_paid - \
            total_deductions - total_taxes_and_charges

        # Update Sales Invoice Sales Team
        # Check if sales_team child table exists
        if not hasattr(sales_invoice, 'sales_team') or not sales_invoice.sales_team:
            frappe.throw(
                _("No Sales Team found in Sales Invoice {0}").format(invoice_name))

        # Update each sales person in sales_team
        updated_count = 0
        sales_persons_details = []  # Store details for each sales person

        for sales_person_row in sales_invoice.sales_team:
            if sales_person_row.sales_person:
                # Get sales person name
                sales_person_name = sales_person_row.sales_person

                # Get commission rate
                # Handle both percentage format (e.g., 5 for 5%) and decimal format (e.g., 0.05)
                # Convert to float to handle string values from database
                commission_rate = sales_person_row.commission_rate
                if commission_rate is None:
                    commission_rate = 0
                else:
                    try:
                        commission_rate = float(commission_rate)
                    except (ValueError, TypeError):
                        commission_rate = 0

                # Store original commission_rate for display
                commission_rate_display = commission_rate

                # Convert commission_rate to decimal if it's greater than 1 (assuming it's a percentage)
                # If commission_rate is already in decimal format (0-1), use it as is
                if commission_rate > 1:
                    commission_rate_decimal = commission_rate / 100
                else:
                    commission_rate_decimal = commission_rate

                # Calculate incentives
                # incentives = commission_rate * net_paid_after_all_deductions
                # Use flt() to round the value like in original ERPNext code
                incentives = flt(
                    commission_rate_decimal * net_paid_after_all_deductions,
                    precision=2  # 2 decimal places for currency
                )

                # Update only incentives field directly on the row
                # Leave allocated_percentage unchanged (keep original value)
                # This follows the same pattern as ERPNext selling_controller.py
                sales_person_row.incentives = incentives

                # Store details for message
                sales_persons_details.append({
                    "name": sales_person_name,
                    "commission_rate": commission_rate_display,
                    "incentives": incentives,
                    "net_paid_after_all_deductions": net_paid_after_all_deductions,
                    "commission_rate_decimal": commission_rate_decimal
                })

                updated_count += 1

        if updated_count == 0:
            frappe.throw(_("No sales persons found in Sales Team to update"))

        # Save the Sales Invoice document
        # This will save all child table changes including incentives
        # Following Frappe framework pattern: update child rows then save parent doc
        sales_invoice.save(ignore_permissions=True)
        frappe.db.commit()

        # Build detailed message with formatted information
        # Format currency values using frappe.format_value
        grand_total_formatted = frappe.format_value(
            grand_total, {'fieldtype': 'Currency', 'currency': currency}, sales_invoice)
        total_taxes_formatted = frappe.format_value(total_taxes_and_charges, {
                                                    'fieldtype': 'Currency', 'currency': currency}, sales_invoice)
        total_paid_formatted = frappe.format_value(
            total_paid, {'fieldtype': 'Currency', 'currency': currency}, payment_entry)
        total_deductions_formatted = frappe.format_value(
            total_deductions, {'fieldtype': 'Currency', 'currency': currency}, payment_entry)
        net_paid_formatted = frappe.format_value(
            net_paid, {'fieldtype': 'Currency', 'currency': currency}, payment_entry)
        net_paid_after_all_formatted = frappe.format_value(net_paid_after_all_deductions, {
                                                           'fieldtype': 'Currency', 'currency': currency}, payment_entry)

        message_parts = [
            "<b>Sales Invoice:</b>",
            "<br>",
            f"Sales Invoice {invoice_name}",
            "<br>",
            f"Grand_Total: {grand_total_formatted}",
            "<br>",
            f"Total_Taxes: {total_taxes_formatted}",
            "<br><br>",
            "<b>Payment Entry:</b>",
            "<br>",
            f"Total_Paid: {total_paid_formatted}",
            "<br>",
            f"Total_Deductions: {total_deductions_formatted}",
            "<br>",
            f"Net Paid: {net_paid_formatted}",
            "<br>",
            f"Net Paid After All: {net_paid_after_all_formatted}",
            "<br><br>",
            "<b>Sales Team:</b>",
            "<br>"
        ]

        for detail in sales_persons_details:
            # Format commission rate for display (percentage format)
            if detail["commission_rate"] > 1:
                commission_rate_display = f"{detail['commission_rate']}%"
            else:
                commission_rate_display = f"{detail['commission_rate'] * 100}%"

            # Format the calculation: net_paid × commission_rate = incentives
            net_paid_formatted = flt(
                detail['net_paid_after_all_deductions'], precision=2)
            incentives_formatted = flt(detail['incentives'], precision=2)
            commission_rate_decimal = detail['commission_rate_decimal']

            message_parts.extend([
                f"Sales Person: {detail['name']}",
                "<br>",
                f"Commission Rate: {commission_rate_display}",
                "<br>",
                f"Incentives: {net_paid_formatted:,.2f} × {commission_rate_decimal} = {incentives_formatted:,.2f}",
                "<br><br>"
            ])

        # Return result
        return {
            "status": "success",
            "message": "".join(message_parts),
            "values": {
                "total_paid": total_paid,
                "total_deductions": total_deductions,
                "net_paid": net_paid,
                "total_taxes_and_charges": total_taxes_and_charges,
                "net_paid_after_all_deductions": net_paid_after_all_deductions,
                "updated_sales_persons": updated_count,
                "sales_persons_details": sales_persons_details
            }
        }

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _(
            "Error calculating net contribution"))
        frappe.throw(
            _("Error calculating net contribution: {0}").format(str(e)))


def on_submit(doc, method=None):
    """
    Automatically calculate net contribution when Payment Entry is submitted
    Only for payment_type = "Receive"
    """
    # Only process Payment Entry with payment_type = "Receive"
    if doc.payment_type != "Receive":
        return

    # Call the calculation function
    try:
        calculate_net_contribution(doc.name)
    except Exception as e:
        # Log error but don't prevent submission
        frappe.log_error(
            frappe.get_traceback(),
            _("Error calculating net contribution on submit for Payment Entry {0}").format(
                doc.name)
        )
