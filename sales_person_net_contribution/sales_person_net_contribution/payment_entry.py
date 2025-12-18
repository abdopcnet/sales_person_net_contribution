"""
Payment Entry Script
Calculate net paid amount after deductions and update Sales Invoice Sales Team

Structure:
1. Field Validation Functions
2. Reference Analysis Functions
3. Deduction Distribution Functions
4. Invoice Processing Functions (per case)
5. Sales Team Update Functions
6. Main Calculation Function
7. Hook Functions (on_validate, on_submit, on_cancel)
"""

import frappe
from frappe import _
from frappe.utils import flt


# ============================================================================
# SECTION 1: FIELD VALIDATION FUNCTIONS
# ============================================================================

def validate_payment_entry_fields(payment_entry):
    """
    Validate required fields in Payment Entry

    Args:
        payment_entry: Payment Entry document

    Returns:
        dict: Validation result with status and message
    """
    if not payment_entry:
        return {
            "status": "error",
            "message": _("Payment Entry document is required")
        }

    if payment_entry.payment_type != "Receive":
        return {
            "status": "skip",
            "message": _("Only Payment Entry with payment_type = 'Receive' is processed")
        }

    if not payment_entry.references:
        return {
            "status": "error",
            "message": _("No references found in Payment Entry")
        }

    return {
        "status": "success",
        "message": "Validation passed"
    }


def validate_payment_entry_name(payment_entry_name):
    """
    Validate and clean Payment Entry name

    Args:
        payment_entry_name: Name of Payment Entry

    Returns:
        str: Cleaned payment entry name

    Raises:
        frappe.ValidationError: If name is invalid or not found
    """
    if not payment_entry_name:
        frappe.throw(_("Payment Entry name is required"))

    payment_entry_name = str(payment_entry_name).strip()

    if not frappe.db.exists("Payment Entry", payment_entry_name):
        frappe.throw(_("Payment Entry {0} not found").format(
            payment_entry_name))

    return payment_entry_name


# ============================================================================
# SECTION 2: REFERENCE ANALYSIS FUNCTIONS
# ============================================================================

def analyze_payment_entry_references(payment_entry):
    """
    Analyze Payment Entry references and categorize by invoice

    Payment Entry References Table Fields:
    - reference_doctype: Type of reference (Sales Invoice, Sales Order, etc.)
    - reference_name: Name of the referenced document
    - allocated_amount: Amount allocated to this reference

    Cases handled:
    1. Single invoice in single row
    2. Single invoice in multiple rows (same invoice repeated)
    3. Multiple different invoices

    Args:
        payment_entry: Payment Entry document

    Returns:
        dict: {
            "sales_invoice_references": {invoice_name: total_allocated_amount},
            "sales_order_references": {order_name: total_allocated_amount},
            "case_type": "single_invoice" | "single_invoice_multiple_rows" | "multiple_invoices"
        }
    """
    sales_invoice_references = {}
    sales_order_references = {}

    # Collect all references
    for reference in payment_entry.references:
        if reference.reference_doctype == "Sales Invoice" and reference.reference_name:
            invoice_name = reference.reference_name
            allocated_amount = flt(reference.allocated_amount or 0)
            if invoice_name in sales_invoice_references:
                sales_invoice_references[invoice_name] += allocated_amount
            else:
                sales_invoice_references[invoice_name] = allocated_amount
        elif reference.reference_doctype == "Sales Order" and reference.reference_name:
            order_name = reference.reference_name
            allocated_amount = flt(reference.allocated_amount or 0)
            if order_name in sales_order_references:
                sales_order_references[order_name] += allocated_amount
            else:
                sales_order_references[order_name] = allocated_amount

    # Determine case type
    invoice_count = len(sales_invoice_references)
    reference_rows_count = sum(1 for r in payment_entry.references
                               if r.reference_doctype == "Sales Invoice" and r.reference_name)

    if invoice_count == 0:
        case_type = "no_invoices"
    elif invoice_count == 1:
        if reference_rows_count == 1:
            case_type = "single_invoice"
        else:
            case_type = "single_invoice_multiple_rows"
    else:
        case_type = "multiple_invoices"

    return {
        "sales_invoice_references": sales_invoice_references,
        "sales_order_references": sales_order_references,
        "case_type": case_type,
        "reference_rows_count": reference_rows_count
    }


# ============================================================================
# SECTION 3: DEDUCTION DISTRIBUTION FUNCTIONS
# ============================================================================

def calculate_total_deductions(payment_entry):
    """
    Calculate total deductions from Payment Entry

    Payment Entry Deductions Table Fields:
    - account: Account for deduction
    - amount: Deduction amount
    - description: Description of deduction
    - is_exchange_gain_loss: Flag for exchange gain/loss

    Args:
        payment_entry: Payment Entry document

    Returns:
        float: Total deductions amount
    """
    total_deductions = 0
    if payment_entry.deductions:
        for deduction in payment_entry.deductions:
            if deduction.amount:
                try:
                    total_deductions += flt(deduction.amount)
                except (ValueError, TypeError):
                    pass
    return total_deductions


def distribute_deductions_to_invoices(sales_invoice_references, total_deductions, total_paid):
    """
    Distribute deductions proportionally to each invoice based on allocated amount

    Formula:
    - deduction_ratio = invoice_allocated_amount / total_paid
    - invoice_deduction = total_deductions * deduction_ratio

    If total_paid is 0, distribute equally

    Args:
        sales_invoice_references: dict {invoice_name: allocated_amount}
        total_deductions: Total deductions amount
        total_paid: Total paid amount

    Returns:
        dict: {invoice_name: deduction_amount}
    """
    invoice_deductions = {}

    if total_paid > 0:
        # Proportional distribution
        for invoice_name, allocated_amount in sales_invoice_references.items():
            deduction_ratio = allocated_amount / total_paid
            invoice_deductions[invoice_name] = total_deductions * \
                deduction_ratio
    else:
        # Equal distribution if total_paid is 0
        if len(sales_invoice_references) > 0:
            equal_deduction = total_deductions / len(sales_invoice_references)
            for invoice_name in sales_invoice_references.keys():
                invoice_deductions[invoice_name] = equal_deduction

    return invoice_deductions


# ============================================================================
# SECTION 4: INVOICE PROCESSING FUNCTIONS (PER CASE)
# ============================================================================

def process_single_invoice_case(payment_entry, payment_entry_name, invoice_name,
                                allocated_amount, invoice_deduction):
    """
    Process Case 1: Single invoice in Payment Entry

    Args:
        payment_entry: Payment Entry document
        payment_entry_name: Name of Payment Entry
        invoice_name: Name of Sales Invoice
        allocated_amount: Allocated amount for this invoice
        invoice_deduction: Deduction amount for this invoice

    Returns:
        dict: Result with status, message, and details
    """
    invoice_net_paid = allocated_amount - invoice_deduction
    return process_single_invoice(
        payment_entry, payment_entry_name, invoice_name,
        allocated_amount, invoice_deduction, invoice_net_paid
    )


def process_single_invoice_multiple_rows_case(payment_entry, payment_entry_name,
                                              invoice_name, total_allocated_amount,
                                              invoice_deduction):
    """
    Process Case 2: Single invoice in multiple rows (same invoice repeated)

    This is the same as Case 1, but we aggregate the allocated amounts first

    Args:
        payment_entry: Payment Entry document
        payment_entry_name: Name of Payment Entry
        invoice_name: Name of Sales Invoice
        total_allocated_amount: Total allocated amount (sum of all rows)
        invoice_deduction: Deduction amount for this invoice

    Returns:
        dict: Result with status, message, and details
    """
    invoice_net_paid = total_allocated_amount - invoice_deduction
    return process_single_invoice(
        payment_entry, payment_entry_name, invoice_name,
        total_allocated_amount, invoice_deduction, invoice_net_paid
    )


def process_multiple_invoices_case(payment_entry, payment_entry_name,
                                   sales_invoice_references, invoice_deductions):
    """
    Process Case 3: Multiple different invoices in Payment Entry

    Args:
        payment_entry: Payment Entry document
        payment_entry_name: Name of Payment Entry
        sales_invoice_references: dict {invoice_name: allocated_amount}
        invoice_deductions: dict {invoice_name: deduction_amount}

    Returns:
        dict: Aggregated result with status, message, and details
    """
    results = []

    for invoice_name, allocated_amount in sales_invoice_references.items():
        invoice_deduction = invoice_deductions.get(invoice_name, 0)
        invoice_net_paid = allocated_amount - invoice_deduction

        result = process_single_invoice(
            payment_entry, payment_entry_name, invoice_name,
            allocated_amount, invoice_deduction, invoice_net_paid
        )
        results.append(result)

    # Build aggregated message
    message_parts = []
    total_updated_persons = 0
    success_count = 0

    for i, result in enumerate(results, 1):
        if result.get("status") == "success":
            success_count += 1
            message_parts.append(
                f"<b>Invoice {i}: {result['invoice_name']}</b><br>")
            message_parts.append(result["message"])
            message_parts.append("<br>")
            total_updated_persons += result.get("updated_persons", 0)
        else:
            message_parts.append(
                f"<b>Error in Invoice {i}: {result.get('invoice_name', 'Unknown')}</b><br>")
            message_parts.append(result.get("error", "Unknown error"))
            message_parts.append("<br>")

    return {
        "status": "success" if success_count > 0 else "error",
        "message": "".join(message_parts),
        "values": {
            "total_invoices": len(results),
            "success_invoices": success_count,
            "total_updated_persons": total_updated_persons,
            "results": results
        }
    }


# ============================================================================
# SECTION 5: SALES TEAM UPDATE FUNCTIONS
# ============================================================================

def get_sales_team_from_invoice(sales_invoice):
    """
    Get Sales Team from Sales Invoice (Priority 1)

    Sales Invoice Sales Team Table Fields:
    - sales_person: Link to Sales Person
    - commission_rate: Commission rate percentage
    - allocated_percentage: Allocated percentage
    - incentives: Calculated incentives
    - custom_payment_entry: Custom field for Payment Entry reference
    - custom_date: Custom field for Payment Entry date

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        list: List of sales team members with their details
    """
    original_sales_team = []
    seen_sales_persons = set()

    if hasattr(sales_invoice, 'sales_team') and sales_invoice.sales_team:
        for sales_person_row in sales_invoice.sales_team:
            if sales_person_row.sales_person and sales_person_row.sales_person not in seen_sales_persons:
                original_sales_team.append({
                    'sales_person': sales_person_row.sales_person,
                    'commission_rate': sales_person_row.commission_rate,
                    'allocated_percentage': sales_person_row.allocated_percentage,
                })
                seen_sales_persons.add(sales_person_row.sales_person)

    return original_sales_team


def get_sales_team_from_sales_order(sales_invoice):
    """
    Get Sales Team from Sales Order (Priority 2)

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        list: List of sales team members with their details
    """
    original_sales_team = []
    seen_sales_persons = set()

    if sales_invoice.get('items'):
        sales_order_name = None
        for item in sales_invoice.items:
            if item.sales_order:
                sales_order_name = item.sales_order
                break

        if sales_order_name:
            try:
                sales_order = frappe.get_doc("Sales Order", sales_order_name)
                if hasattr(sales_order, 'sales_team') and sales_order.sales_team:
                    for sales_person_row in sales_order.sales_team:
                        if sales_person_row.sales_person and sales_person_row.sales_person not in seen_sales_persons:
                            original_sales_team.append({
                                'sales_person': sales_person_row.sales_person,
                                'commission_rate': sales_person_row.commission_rate,
                                'allocated_percentage': sales_person_row.allocated_percentage,
                            })
                            seen_sales_persons.add(
                                sales_person_row.sales_person)
            except frappe.DoesNotExistError:
                pass

    return original_sales_team


def get_sales_team_from_customer(sales_invoice):
    """
    Get Sales Team from Customer (Priority 3)

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        list: List of sales team members with their details
    """
    original_sales_team = []
    seen_sales_persons = set()

    if sales_invoice.customer:
        try:
            customer = frappe.get_doc("Customer", sales_invoice.customer)
            if hasattr(customer, 'sales_team') and customer.sales_team:
                for sales_person_row in customer.sales_team:
                    if sales_person_row.sales_person and sales_person_row.sales_person not in seen_sales_persons:
                        original_sales_team.append({
                            'sales_person': sales_person_row.sales_person,
                            'commission_rate': sales_person_row.commission_rate,
                            'allocated_percentage': sales_person_row.allocated_percentage,
                        })
                        seen_sales_persons.add(sales_person_row.sales_person)
        except frappe.DoesNotExistError:
            pass

    return original_sales_team


def get_original_sales_team(sales_invoice):
    """
    Get original Sales Team structure from Sales Invoice, Sales Order, or Customer
    Priority: Sales Invoice -> Sales Order -> Customer

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        list: List of sales team members with their details
    """
    # Priority 1: Sales Invoice
    original_sales_team = get_sales_team_from_invoice(sales_invoice)

    # Priority 2: Sales Order
    if not original_sales_team:
        original_sales_team = get_sales_team_from_sales_order(sales_invoice)

    # Priority 3: Customer
    if not original_sales_team:
        original_sales_team = get_sales_team_from_customer(sales_invoice)

    return original_sales_team


def update_sales_team_for_payment_entry(sales_invoice, payment_entry_name,
                                        payment_entry_date, original_sales_team,
                                        net_paid_after_all_deductions):
    """
    Update or create Sales Team rows for Payment Entry

    Logic:
    1. Delete rows without custom_payment_entry (generic rows)
    2. For each sales person:
       - If row exists with same custom_payment_entry and sales_person: UPDATE
       - Else: CREATE new row

    Args:
        sales_invoice: Sales Invoice document
        payment_entry_name: Name of Payment Entry
        payment_entry_date: Date of Payment Entry
        original_sales_team: List of original sales team members
        net_paid_after_all_deductions: Net paid amount after all deductions

    Returns:
        dict: {
            "updated_count": int,
            "sales_persons_details": list
        }
    """
    # Step 1: Delete rows without custom_payment_entry
    rows_to_remove = []
    for sales_person_row in sales_invoice.sales_team:
        if not getattr(sales_person_row, 'custom_payment_entry', None):
            rows_to_remove.append(sales_person_row)

    for row in rows_to_remove:
        sales_invoice.remove(row)

    # Step 2: Update or create rows for each sales person
    updated_count = 0
    sales_persons_details = []

    for sales_person_data in original_sales_team:
        if not sales_person_data.get('sales_person'):
            continue

        sales_person_name = sales_person_data['sales_person']

        # Get commission rate
        commission_rate = sales_person_data.get('commission_rate')
        if commission_rate is None:
            commission_rate = 0
        else:
            try:
                commission_rate = flt(commission_rate)
            except (ValueError, TypeError):
                commission_rate = 0

        commission_rate_display = commission_rate

        # Convert commission_rate to decimal if it's greater than 1
        if commission_rate > 1:
            commission_rate_decimal = commission_rate / 100
        else:
            commission_rate_decimal = commission_rate

        # Calculate incentives
        incentives = flt(
            commission_rate_decimal * net_paid_after_all_deductions,
            precision=2
        )

        # Check if row exists with same custom_payment_entry and sales_person
        existing_row = None
        for row in sales_invoice.sales_team:
            if (getattr(row, 'custom_payment_entry', None) == payment_entry_name and
                    row.sales_person == sales_person_name):
                existing_row = row
                break

        if existing_row:
            # Update existing row
            existing_row.commission_rate = commission_rate_display
            existing_row.allocated_percentage = sales_person_data.get(
                'allocated_percentage', 0)
            existing_row.incentives = incentives
            existing_row.custom_payment_entry = payment_entry_name
            existing_row.custom_date = payment_entry_date
        else:
            # Create new row in Sales Team
            sales_invoice.append('sales_team', {
                'sales_person': sales_person_name,
                'commission_rate': commission_rate_display,
                'allocated_percentage': sales_person_data.get('allocated_percentage', 0),
                'incentives': incentives,
                'custom_payment_entry': payment_entry_name,
                'custom_date': payment_entry_date,
            })

        # Store details for message
        sales_persons_details.append({
            "name": sales_person_name,
            "commission_rate": commission_rate_display,
            "incentives": incentives,
            "net_paid_after_all_deductions": net_paid_after_all_deductions,
            "commission_rate_decimal": commission_rate_decimal
        })

        updated_count += 1

    return {
        "updated_count": updated_count,
        "sales_persons_details": sales_persons_details
    }


def remove_sales_team_for_payment_entry(sales_invoice, payment_entry_name):
    """
    Remove Sales Team rows associated with Payment Entry (for cancel)

    Args:
        sales_invoice: Sales Invoice document
        payment_entry_name: Name of Payment Entry to remove

    Returns:
        int: Number of rows removed
    """
    rows_to_remove = []
    for sales_person_row in sales_invoice.sales_team:
        if getattr(sales_person_row, 'custom_payment_entry', None) == payment_entry_name:
            rows_to_remove.append(sales_person_row)

    for row in rows_to_remove:
        sales_invoice.remove(row)

    return len(rows_to_remove)


# ============================================================================
# SECTION 6: PAYMENT ENTRY REFERENCES UPDATE FUNCTIONS
# ============================================================================

def calculate_tax_amount_from_invoice(sales_invoice, allocated_amount):
    """
    Calculate tax amount from allocated amount based on invoice tax rate

    Formula:
    - If grand_total > 0: tax_ratio = total_taxes_and_charges / grand_total
    - tax_amount = allocated_amount * tax_ratio

    Args:
        sales_invoice: Sales Invoice document
        allocated_amount: Allocated amount for this invoice

    Returns:
        float: Tax amount proportional to allocated amount
    """
    try:
        grand_total = flt(sales_invoice.grand_total or 0)
        total_taxes_and_charges = flt(
            sales_invoice.total_taxes_and_charges or 0)

        if grand_total > 0:
            tax_ratio = total_taxes_and_charges / grand_total
            tax_amount = allocated_amount * tax_ratio
        else:
            tax_amount = 0

        return flt(tax_amount, precision=2)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def update_payment_entry_references(payment_entry_name, invoice_name,
                                    total_allocated_amount, total_invoice_deduction,
                                    sales_invoice):
    """
    Update custom fields in Payment Entry References table for the invoice

    Fields to update:
    - custom_tax_amount_from_allocated: Tax amount calculated from allocated amount
    - custom_net_without_tax_without_deductions: allocated_amount - tax_amount - deducted
      (Net amount without tax and without deductions)
    - custom_net_without_tax: allocated_amount - tax_amount (Net amount without tax only)

    Formula:
    - tax_amount = (total_taxes_and_charges / grand_total) * allocated_amount
    - custom_net_without_tax_without_deductions = allocated_amount - tax_amount - deducted
    - custom_net_without_tax = allocated_amount - tax_amount

    If invoice appears in multiple rows, values are distributed proportionally based on allocated_amount in each row

    Args:
        payment_entry_name: Name of Payment Entry
        invoice_name: Name of Sales Invoice
        total_allocated_amount: Total allocated amount for this invoice across all rows
        total_invoice_deduction: Total deduction amount for this invoice
        sales_invoice: Sales Invoice document
    """
    try:
        # Get all reference rows for this invoice with their allocated amounts
        reference_rows = frappe.get_all(
            "Payment Entry Reference",
            filters={
                "parent": payment_entry_name,
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice_name
            },
            fields=["name", "allocated_amount"]
        )

        if not reference_rows:
            return

        # Calculate total allocated amount from all rows for this invoice
        total_row_allocated = sum(flt(row.allocated_amount or 0)
                                  for row in reference_rows)

        if total_row_allocated == 0:
            return

        # Update each reference row proportionally
        for row in reference_rows:
            row_allocated = flt(row.allocated_amount or 0)

            # Calculate proportional values for this row
            if total_row_allocated > 0:
                ratio = row_allocated / total_row_allocated
                row_allocated_proportional = total_allocated_amount * ratio
                row_deduction_proportional = total_invoice_deduction * ratio
            else:
                # If total is 0, distribute equally
                row_count = len(reference_rows)
                row_allocated_proportional = total_allocated_amount / \
                    row_count if row_count > 0 else 0
                row_deduction_proportional = total_invoice_deduction / \
                    row_count if row_count > 0 else 0

            # Calculate tax amount for this row
            row_tax_amount = calculate_tax_amount_from_invoice(
                sales_invoice, row_allocated_proportional)

            # Calculate custom_net_without_tax_without_deductions
            # Formula: allocated_amount - tax_amount - deducted
            row_net_without_tax_without_deductions = row_allocated_proportional - \
                row_tax_amount - row_deduction_proportional

            # Calculate custom_net_without_tax
            # Formula: allocated_amount - tax_amount (only tax, no deductions)
            row_net_without_tax = row_allocated_proportional - row_tax_amount

            # Update the row
            frappe.db.set_value(
                "Payment Entry Reference",
                row.name,
                {
                    "custom_tax_amount_from_allocated": flt(row_tax_amount, precision=2),
                    "custom_net_without_tax_without_deductions": flt(row_net_without_tax_without_deductions, precision=2),
                    "custom_net_without_tax": flt(row_net_without_tax, precision=2)
                }
            )

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            _("Error updating Payment Entry References for invoice {0}").format(
                invoice_name)
        )


# ============================================================================
# SECTION 7: SINGLE INVOICE PROCESSING FUNCTION
# ============================================================================

def process_single_invoice(payment_entry, payment_entry_name, invoice_name,
                           allocated_amount, invoice_deduction, invoice_net_paid):
    """
    Process a single Sales Invoice to update Sales Team with net contribution

    This function handles all cases where we process one invoice at a time

    Args:
        payment_entry: Payment Entry document
        payment_entry_name: Name of Payment Entry
        invoice_name: Name of Sales Invoice
        allocated_amount: Allocated amount for this invoice
        invoice_deduction: Deduction amount for this invoice
        invoice_net_paid: Net paid amount for this invoice (after deduction)

    Returns:
        dict: Result with status, message, and details
    """
    try:
        # Get Sales Invoice document
        sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)

        # Get total taxes and charges from Sales Invoice
        try:
            total_taxes_and_charges = flt(
                sales_invoice.total_taxes_and_charges or 0)
        except (ValueError, TypeError):
            total_taxes_and_charges = 0

        # Get grand total from Sales Invoice
        try:
            grand_total = flt(sales_invoice.grand_total or 0)
        except (ValueError, TypeError):
            grand_total = 0

        # Get currency from Payment Entry or Sales Invoice
        currency = payment_entry.paid_to_account_currency or payment_entry.company_currency or sales_invoice.currency or "EGP"

        # Calculate net_paid_after_all_deductions for this invoice
        net_paid_after_all_deductions = invoice_net_paid - total_taxes_and_charges

        # Get original Sales Team structure
        original_sales_team = get_original_sales_team(sales_invoice)

        # If still no Sales Team found, return error
        if not original_sales_team:
            return {
                "status": "error",
                "invoice_name": invoice_name,
                "error": _("Sales Team not found in invoice {0}, order, or customer. Please add Sales Team members first.").format(invoice_name)
            }

        # Update Sales Team
        payment_entry_date = payment_entry.posting_date or frappe.utils.today()
        update_result = update_sales_team_for_payment_entry(
            sales_invoice, payment_entry_name, payment_entry_date,
            original_sales_team, net_paid_after_all_deductions
        )

        if update_result["updated_count"] == 0:
            return {
                "status": "error",
                "invoice_name": invoice_name,
                "error": _("No sales persons found in Sales Team to update")
            }

        # Save the Sales Invoice document
        sales_invoice.save(ignore_permissions=True)
        frappe.db.commit()

        # Update Payment Entry References table with calculated values
        # This updates the custom fields to show calculation details for each invoice
        update_payment_entry_references(
            payment_entry_name, invoice_name,
            allocated_amount, invoice_deduction,
            sales_invoice
        )

        # Build message for this invoice
        grand_total_formatted = frappe.format_value(
            grand_total, {'fieldtype': 'Currency', 'currency': currency}, sales_invoice)
        total_taxes_formatted = frappe.format_value(total_taxes_and_charges, {
            'fieldtype': 'Currency', 'currency': currency}, sales_invoice)
        allocated_amount_formatted = frappe.format_value(
            allocated_amount, {'fieldtype': 'Currency', 'currency': currency}, payment_entry)
        invoice_deduction_formatted = frappe.format_value(
            invoice_deduction, {'fieldtype': 'Currency', 'currency': currency}, payment_entry)
        invoice_net_paid_formatted = frappe.format_value(
            invoice_net_paid, {'fieldtype': 'Currency', 'currency': currency}, payment_entry)
        net_paid_after_all_formatted = frappe.format_value(net_paid_after_all_deductions, {
            'fieldtype': 'Currency', 'currency': currency}, payment_entry)

        # Uniform font size with minimal spacing
        uniform_style = 'style="font-size: 12px; line-height: 1.3; color: #2c3e50; margin: 0; padding: 0;"'
        header_style = 'style="font-size: 12px; font-weight: bold; color: #2c3e50; margin: 0; padding: 0; margin-top: 2px;"'

        message_parts = [
            f'<div {header_style}>Sales Invoice: {invoice_name}</div>',
            f'<div {uniform_style}>Grand Total: {grand_total_formatted}</div>',
            f'<div {uniform_style}>Total Taxes: {total_taxes_formatted}</div>',
            f'<div {header_style}>Payment Entry:</div>',
            f'<div {uniform_style}>Allocated Amount: {allocated_amount_formatted}</div>',
            f'<div {uniform_style}>Deductions: {invoice_deduction_formatted}</div>',
            f'<div {uniform_style}>Net Paid: {invoice_net_paid_formatted}</div>',
            f'<div {uniform_style}>Net Paid After All Deductions: {net_paid_after_all_formatted}</div>',
            f'<div {header_style}>Sales Team:</div>'
        ]

        for detail in update_result["sales_persons_details"]:
            if detail["commission_rate"] > 1:
                commission_rate_display = f"{detail['commission_rate']}%"
            else:
                commission_rate_display = f"{detail['commission_rate'] * 100}%"

            net_paid_formatted = flt(
                detail['net_paid_after_all_deductions'], precision=2)
            incentives_formatted = flt(detail['incentives'], precision=2)
            commission_rate_decimal = detail['commission_rate_decimal']

            message_parts.extend([
                f'<div {uniform_style}>Sales Person: {detail["name"]}</div>',
                f'<div {uniform_style}>Commission Rate: {commission_rate_display}</div>',
                f'<div {uniform_style}>Incentives: {net_paid_formatted:,.2f} × {commission_rate_decimal} = {incentives_formatted:,.2f}</div>'
            ])

        return {
            "status": "success",
            "invoice_name": invoice_name,
            "message": "".join(message_parts),
            "updated_persons": update_result["updated_count"],
            "values": {
                "allocated_amount": allocated_amount,
                "invoice_deduction": invoice_deduction,
                "invoice_net_paid": invoice_net_paid,
                "total_taxes_and_charges": total_taxes_and_charges,
                "net_paid_after_all_deductions": net_paid_after_all_deductions,
                "sales_persons_details": update_result["sales_persons_details"]
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _(
            "Error processing invoice {0}").format(invoice_name))
        return {
            "status": "error",
            "invoice_name": invoice_name,
            "error": _("Error processing invoice: {0}").format(str(e))
        }


# ============================================================================
# SECTION 8: MESSAGE GENERATION FUNCTIONS
# ============================================================================

def generate_status_message(payment_entry, references_analysis, sales_invoice_references):
    """
    Generate status message explaining the case and what will be done

    Args:
        payment_entry: Payment Entry document
        references_analysis: Result from analyze_payment_entry_references
        sales_invoice_references: dict {invoice_name: allocated_amount}

    Returns:
        str: Formatted status message in Arabic with RTL styling
    """
    case_type = references_analysis["case_type"]
    invoice_count = len(sales_invoice_references)

    # Get customer name from first invoice
    customer_name = ""
    if sales_invoice_references:
        first_invoice_name = list(sales_invoice_references.keys())[0]
        try:
            first_invoice = frappe.get_doc("Sales Invoice", first_invoice_name)
            customer_name = first_invoice.customer_name or first_invoice.customer or ""
        except:
            pass

    # LTR styling
    rtl_style = 'style="direction: ltr; text-align: left; font-family: Arial, sans-serif;"'
    header_style = 'style="direction: ltr; text-align: left; font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #3498db;"'
    item_style = 'style="direction: ltr; text-align: left; padding: 8px 0; font-size: 14px; line-height: 1.6;"'
    bullet_style = 'style="color: #3498db; margin-right: 10px; margin-left: 5px;"'

    message_parts = [f'<div {rtl_style}>']

    if case_type == "single_invoice":
        message_parts.append(
            f'<div {header_style}>Case: Single invoice for customer <span style="color: #27ae60;">{customer_name}</span></div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Fetch sales person and update invoice</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Update sales person commission rate</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Record Payment Entry reference in Sales Team</div>')

    elif case_type == "single_invoice_multiple_rows":
        message_parts.append(
            f'<div {header_style}>Case: Single invoice (multiple rows) for customer <span style="color: #27ae60;">{customer_name}</span></div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Aggregate allocated amounts from all rows</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Fetch sales person and update invoice</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Update sales person commission rate</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Record Payment Entry reference in Sales Team</div>')

    elif case_type == "multiple_invoices":
        invoice_names = ", ".join(sales_invoice_references.keys())
        message_parts.append(
            f'<div {header_style}>Case: {invoice_count} invoices for customer <span style="color: #27ae60;">{customer_name}</span></div>')
        message_parts.append(
            f'<div style="direction: ltr; text-align: left; margin: 10px 0; padding: 8px; background-color: #ecf0f1; border-radius: 5px;"><b>Invoices:</b> <span style="color: #2980b9;">{invoice_names}</span></div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Distribute deductions proportionally by allocated amount</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Fetch sales person and update invoices</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Update sales person commission rate</div>')
        message_parts.append(
            f'<div {item_style}><span {bullet_style}>•</span> Record Payment Entry reference in Sales Team for each invoice</div>')

    else:
        message_parts.append(
            f'<div {header_style}>Case: Unknown case type</div>')

    message_parts.append('</div>')
    return "".join(message_parts)


def generate_summary_message(payment_entry, references_analysis, sales_invoice_references,
                             invoice_deductions, results):
    """
    Generate summary message showing calculation details for each invoice

    Args:
        payment_entry: Payment Entry document
        references_analysis: Result from analyze_payment_entry_references
        sales_invoice_references: dict {invoice_name: allocated_amount}
        invoice_deductions: dict {invoice_name: deduction_amount}
        results: List of processing results

    Returns:
        str: Formatted summary message in Arabic with RTL styling
    """
    # Uniform font size with minimal spacing
    uniform_style = 'style="font-size: 12px; line-height: 1.3; color: #2c3e50; margin: 0; padding: 0;"'
    header_style = 'style="font-size: 12px; font-weight: bold; color: #2c3e50; margin: 0; padding: 0; border-bottom: 1px solid #27ae60; padding-bottom: 2px; margin-bottom: 2px;"'
    invoice_header_style = 'style="font-size: 12px; font-weight: bold; color: #2980b9; margin: 0; padding: 0; margin-top: 2px;"'
    calc_style = 'style="font-size: 12px; line-height: 1.3; color: #34495e; margin: 0; padding: 0;"'
    value_style = 'style="color: #27ae60; font-weight: bold;"'

    message_parts = ['<div>']
    message_parts.append(f'<div {header_style}>Calculation Summary</div>')

    case_type = references_analysis["case_type"]

    for invoice_name, allocated_amount in sales_invoice_references.items():
        invoice_deduction = invoice_deductions.get(invoice_name, 0)

        # Get invoice details
        try:
            sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)
            grand_total = flt(sales_invoice.grand_total or 0)
            total_taxes = flt(sales_invoice.total_taxes_and_charges or 0)

            # Calculate tax amount from allocated amount
            tax_amount = calculate_tax_amount_from_invoice(
                sales_invoice, allocated_amount)

            # Calculate net_without_tax_rate_without_deductions
            net_without_tax_rate_without_deductions = allocated_amount - \
                tax_amount - invoice_deduction

            # Format values (without currency symbol)
            allocated_formatted = f"{flt(allocated_amount, 2):,.2f}"
            tax_formatted = f"{flt(tax_amount, 2):,.2f}"
            deduction_formatted = f"{flt(invoice_deduction, 2):,.2f}"
            net_formatted = f"{flt(net_without_tax_rate_without_deductions, 2):,.2f}"

            message_parts.append(
                f'<div {invoice_header_style}>📄 {invoice_name}</div>')
            message_parts.append(
                f'<div {calc_style}>Allocated Amount: <span {value_style}>{allocated_formatted}</span></div>')
            message_parts.append(
                f'<div {calc_style}>Tax ({flt(total_taxes/grand_total*100 if grand_total > 0 else 0, precision=1)}%): <span {value_style}>- {tax_formatted}</span></div>')
            message_parts.append(
                f'<div {calc_style}>Deductions: <span {value_style}>- {deduction_formatted}</span></div>')
            message_parts.append(
                f'<div {calc_style}><b>Net without tax and deductions: <span style="color: #e74c3c; font-weight: bold;">{net_formatted}</span></b></div>')

        except Exception as e:
            message_parts.append(
                f'<div {invoice_header_style}>📄 {invoice_name}</div>')
            message_parts.append(
                f'<div {calc_style} style="color: #e74c3c;">Error calculating details: {str(e)}</div>')

    message_parts.append('</div>')
    return "".join(message_parts)


def generate_completion_message(case_type, results, customer_name=""):
    """
    Generate completion message after processing

    Args:
        case_type: Type of case processed
        results: List of results from processing
        customer_name: Customer name

    Returns:
        str: Formatted completion message in English with compact styling
    """
    # Uniform font size with minimal spacing
    item_style = 'style="font-size: 12px; line-height: 1.3; color: #2c3e50; margin: 0; padding: 0;"'

    message_parts = ['<div>']

    if case_type == "single_invoice" or case_type == "single_invoice_multiple_rows":
        if results and results[0].get("status") == "success":
            message_parts.append(
                f'<div {item_style}>✅️ Updated Sales Person</div>')
            message_parts.append(
                f'<div {item_style}>✅️ Updated Sales Person incentives</div>')
            message_parts.append(
                f'<div {item_style}>✅️ Updated Payment Reference</div>')
        else:
            message_parts.append(
                f'<div {item_style} style="color: #e74c3c;">❌ Error: Failed to update invoice</div>')

    elif case_type == "multiple_invoices":
        success_count = sum(1 for r in results if r.get("status") == "success")
        total_count = len(results)

        if success_count > 0:
            message_parts.append(
                f'<div {item_style}>✅️ Updated Sales Person</div>')
            message_parts.append(
                f'<div {item_style}>✅️ Updated Sales Person incentives</div>')
            message_parts.append(
                f'<div {item_style}>✅️ Updated Payment Reference</div>')
            message_parts.append(
                f'<div {item_style} style="color: #27ae60;">Processed: {success_count} of {total_count} invoices</div>')
        else:
            message_parts.append(
                f'<div {item_style} style="color: #e74c3c;">❌ Error: Failed to process all invoices</div>')

    message_parts.append('</div>')
    return "".join(message_parts)


# ============================================================================
# SECTION 9: MAIN CALCULATION FUNCTION
# ============================================================================

@frappe.whitelist()
def calculate_net_contribution(payment_entry_name):
    """
    Main function to calculate net paid after all deductions and update Sales Invoice Sales Team

    Flow:
    1. Validate Payment Entry name
    2. Get Payment Entry document
    3. Validate fields
    4. Analyze references (determine case type)
    5. Calculate total deductions
    6. Distribute deductions to invoices
    7. Process invoices based on case type
    8. Return aggregated result

    Args:
        payment_entry_name: Name of the Payment Entry document

    Returns:
        dict: Result message and calculated values
    """
    try:
        # Step 1: Validate Payment Entry name
        payment_entry_name = validate_payment_entry_name(payment_entry_name)

        # Step 2: Get Payment Entry document
        payment_entry = frappe.get_doc("Payment Entry", payment_entry_name)

        # Step 3: Validate fields
        validation_result = validate_payment_entry_fields(payment_entry)
        if validation_result["status"] == "error":
            frappe.throw(validation_result["message"])
        if validation_result["status"] == "skip":
            return {
                "status": "skipped",
                "message": validation_result["message"]
            }

        # Step 4: Analyze references
        references_analysis = analyze_payment_entry_references(payment_entry)

        # For now, only support Sales Invoice
        if references_analysis["sales_order_references"]:
            frappe.throw(
                _("Sales Order support will be added later. Please use Sales Invoice only."))

        if not references_analysis["sales_invoice_references"]:
            frappe.throw(_("No Sales Invoice found in references"))

        # Step 4.5: Validate only Case 1 (single invoice) is allowed
        case_type = references_analysis["case_type"]
        if case_type != "single_invoice":
            frappe.throw(_("Only one invoice allowed"))

        # Step 5: Calculate total deductions
        total_deductions = calculate_total_deductions(payment_entry)

        # Step 6: Get total paid amount
        try:
            total_paid = flt(payment_entry.total_allocated_amount or 0)
        except (ValueError, TypeError):
            total_paid = 0

        # Step 7: Distribute deductions to invoices
        invoice_deductions = distribute_deductions_to_invoices(
            references_analysis["sales_invoice_references"],
            total_deductions,
            total_paid
        )

        # Step 8: Process Case 1 only (single invoice)
            invoice_name = list(
                references_analysis["sales_invoice_references"].keys())[0]
            allocated_amount = references_analysis["sales_invoice_references"][invoice_name]
            invoice_deduction = invoice_deductions.get(invoice_name, 0)

            result = process_single_invoice_case(
                payment_entry, payment_entry_name, invoice_name,
                allocated_amount, invoice_deduction
            )

            # Add completion and summary messages
            if result.get("status") == "success":
                completion_msg = generate_completion_message(
                    case_type, [result]
                )
                summary_msg = generate_summary_message(
                    payment_entry, references_analysis,
                    references_analysis["sales_invoice_references"],
                    invoice_deductions, [result]
                )
            # Combine messages: completion + summary + details (minimal spacing)
                if result.get("message"):
                    result["message"] = completion_msg + \
                    "<div style='margin-top: 2px;'></div>" + summary_msg + \
                    "<div style='margin-top: 2px;'></div>" + result["message"]

            return {
                "status": result.get("status", "success"),
                "message": result.get("message", ""),
                "values": result.get("values", {})
            }

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _(
            "Error calculating net contribution"))
        frappe.throw(_("Calculation error"))


# ============================================================================
# SECTION 10: HOOK FUNCTIONS
# ============================================================================

def on_validate(doc, method=None):
    """
    Automatically calculate net contribution when Payment Entry is validated (on save)
    Only for payment_type = "Receive"
    """
    if doc.payment_type != "Receive":
        return

    try:
        calculate_net_contribution(doc.name)
    except Exception as e:
        # Log error but don't prevent save
        frappe.log_error(
            frappe.get_traceback(),
            _("Error calculating net contribution on validate for Payment Entry {0}").format(
                doc.name)
        )


def on_submit(doc, method=None):
    """
    Automatically calculate net contribution when Payment Entry is submitted
    Only for payment_type = "Receive"
    """
    if doc.payment_type != "Receive":
        return

    try:
        calculate_net_contribution(doc.name)
    except Exception as e:
        # Log error but don't prevent submission
        frappe.log_error(
            frappe.get_traceback(),
            _("Error calculating net contribution on submit for Payment Entry {0}").format(
                doc.name)
        )


def on_cancel(doc, method=None):
    """
    Remove Sales Team entries associated with this Payment Entry when cancelled
    Only for payment_type = "Receive"
    """
    if doc.payment_type != "Receive":
        return

    try:
        # Analyze references to get all Sales Invoices
        references_analysis = analyze_payment_entry_references(doc)

        # Process each Sales Invoice to remove Payment Entry references
        for invoice_name in references_analysis["sales_invoice_references"].keys():
            try:
                sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)
                removed_count = remove_sales_team_for_payment_entry(
                    sales_invoice, doc.name)

                if removed_count > 0:
                    sales_invoice.save(ignore_permissions=True)
                    frappe.db.commit()

                    frappe.msgprint(
                        _("Deleted {0} row(s) from Sales Team in invoice {1}").format(
                            removed_count, invoice_name),
                        indicator="green"
                    )
            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(),
                    _("Error removing sales person commission from invoice {0} on cancel Payment Entry {1}").format(
                        invoice_name, doc.name)
                )
    except Exception as e:
        # Log error but don't prevent cancellation
        frappe.log_error(
            frappe.get_traceback(),
            _("Error removing sales person commission on cancel Payment Entry {0}").format(
                doc.name)
        )
