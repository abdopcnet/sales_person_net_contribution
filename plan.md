# Payment Entry Net Contribution Script Plan

## Overview

Create a script on Payment Entry that calculates net paid amount after deductions and updates Sales Invoice Sales Team allocated_percentage.

## Requirements

### Button Functionality

-   Add a button to Payment Entry form
-   On button click, execute the calculation logic

### Data Reading

1. Read child table `references` (Payment Entry Reference)

    - Check for Sales Invoice (reference_doctype = "Sales Invoice")
    - Check for Sales Order (reference_doctype = "Sales Order")
    - Get reference_name (e.g., ACC-SINV-2025-00223)

2. Read child table `deductions` (Payment Entry Deduction)
    - Sum all `amount` values from all rows
    - Store as `total_deductions`

### Calculation Logic

-   Only process if:

    -   One invoice exists in references table (Sales Invoice or Sales Order)
    -   Payment Entry is submitted (docstatus = 1)

-   Calculate:
    -   `total_deductions` = sum of all deductions.amount (0 if no deductions)
    -   `total_paid` = Payment Entry.total_allocated_amount
    -   `net_paid` = total_paid - total_deductions
    -   `net_paid_after_all_deductions` = total_paid - total_deductions - Sales Invoice.total_taxes_and_charges

### Update Sales Invoice

-   Find Sales Invoice: tabSales Invoice.name = reference_name
-   Update child table: tabSales Team
-   For each sales person in sales_team:
    -   Get commission_rate from sales_team row
    -   Convert commission_rate to decimal if > 1 (assume percentage format)
    -   Calculate: `incentives = commission_rate * net_paid_after_all_deductions`
    -   Update `incentives` field only
    -   Leave `allocated_percentage` unchanged (keep original value)

### Example

-   Payment Entry: ACC-PAY-2025-00380
-   total_allocated_amount = 4,300
-   Total deductions = 37.80
-   Invoice: ACC-SINV-2025-00223
-   Invoice total_taxes_and_charges = 528.0702
-   Calculation: 4,300 - 37.80 - 528.0702 = 3734.1298
-   For sales person with commission_rate (e.g., 5% = 0.05):
    -   allocated_percentage = unchanged (keep original value, e.g., 100%)
    -   incentives = 0.05 \* 3734.1298 = 186.70649

## Implementation Files

1. Server Script: `sales_person_net_contribution/sales_person_net_contribution/payment_entry.py`
2. Client Script: `sales_person_net_contribution/public/js/payment_entry.js`
3. Update hooks.py to include client script
