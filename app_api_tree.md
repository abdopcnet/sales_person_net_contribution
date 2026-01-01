# API Structure - Sales Person Net Contribution

## Whitelisted API Methods

### 1. `calculate_net_contribution`

**Path:** `sales_person_net_contribution.sales_person_net_contribution.payment_entry.calculate_net_contribution`

**Description:** Main function to calculate net paid amount after deductions and update Sales Invoice Sales Team

**Parameters:**

-   `payment_entry_name` (str): Name of the Payment Entry document

**Returns:**

```json
{
  "status": "success" | "error" | "skipped",
  "message": "Formatted HTML message with calculation details",
  "values": {
    "allocated_amount": float,
    "invoice_deduction": float,
    "invoice_net_paid": float,
    "total_taxes_and_charges": float,
    "net_paid_after_all_deductions": float,
    "sales_persons_details": [
      {
        "name": str,
        "commission_rate": float,
        "commission_rate_decimal": float,
        "net_paid_after_all_deductions": float,
        "incentives": float
      }
    ]
  }
}
```

**Flow:**

1. Validate Payment Entry name
2. Get Payment Entry document
3. Validate fields (payment_type = "Receive", references exist)
4. Analyze references (determine case type)
5. Calculate total deductions
6. Distribute deductions to invoices
7. Process invoices based on case type
8. Update Sales Invoice Sales Team
9. Return aggregated result

---

## Internal Functions (Not Whitelisted)

### Validation Functions

-   `validate_payment_entry_fields(payment_entry)` - Validate required fields
-   `validate_payment_entry_name(payment_entry_name)` - Validate and clean name

### Reference Analysis

-   `analyze_payment_entry_references(payment_entry)` - Analyze and categorize references

### Deduction Distribution

-   `calculate_total_deductions(payment_entry)` - Sum all deduction amounts
-   `distribute_deductions_to_invoices(sales_invoice_references, total_deductions, total_paid)` - Proportional distribution

### Invoice Processing

-   `process_single_invoice_case(...)` - Case 1: Single invoice
-   `process_single_invoice_multiple_rows_case(...)` - Case 2: Single invoice, multiple rows
-   `process_multiple_invoices_case(...)` - Case 3: Multiple invoices
-   `process_single_invoice(...)` - Core processing logic

### Sales Team Management

-   `get_sales_team_from_invoice(sales_invoice)` - Priority 1: From invoice
-   `get_sales_team_from_sales_order(sales_invoice)` - Priority 2: From sales order
-   `update_sales_team_for_payment_entry(...)` - Update Sales Team table
-   `remove_sales_team_for_payment_entry(sales_invoice, payment_entry_name)` - Remove entries

### Message Generation

-   `generate_status_message(...)` - Status explanation
-   `generate_summary_message(...)` - Calculation summary
-   `generate_completion_message(...)` - Completion message

---

## Client-Side API Calls

### JavaScript Method Call

```javascript
frappe.call({
	method: 'sales_person_net_contribution.sales_person_net_contribution.payment_entry.calculate_net_contribution',
	args: {
		payment_entry_name: frm.doc.name,
	},
	callback: function (r) {
		// Handle response
	},
});
```

---

## Hook Functions

### Document Events (hooks.py)

-   `on_validate(doc, method)` - Auto-calculate on save (existing documents only)
-   `on_submit(doc, method)` - Auto-calculate on submit
-   `on_cancel(doc, method)` - Remove Sales Team entries on cancel
