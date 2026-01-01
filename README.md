# Sales Person Net Contribution

![Version](https://img.shields.io/badge/version-1.1.2026-blue)


**App Name:** `sales_person_net_contribution`
**Version:** 1.0.0
**License:** MIT

## Overview

Sales Person Net Contribution is a Frappe/ERPNext app that automatically calculates net paid amounts after deductions and updates Sales Invoice Sales Team with commission information based on Payment Entry transactions.

## Key Features

### 1. Automatic Net Contribution Calculation

-   Calculates net paid amount after all deductions from Payment Entry
-   Distributes deductions proportionally across multiple invoices
-   Updates Sales Invoice Sales Team with calculated commission rates

### 2. Payment Entry Integration

-   Works with Payment Entry documents (payment_type = "Receive")
-   Supports single invoice and multiple invoice scenarios
-   Real-time calculation of custom fields in references table

### 3. Sales Team Commission Tracking

-   Automatically fetches Sales Team from Sales Invoice or Sales Order
-   Calculates incentives based on net paid amount and commission rate
-   Records Payment Entry reference in Sales Team for audit trail

### 4. Three Processing Cases

-   **Case 1:** Single invoice in single row
-   **Case 2:** Single invoice in multiple rows (aggregated)
-   **Case 3:** Multiple different invoices (proportional distribution)

### 5. Sales Commission Report

-   Comprehensive report showing:
    -   Invoice details and customer information
    -   Sales person and commission rates
    -   Paid amounts and total deductions
    -   Payment entry references and dates
-   Filterable by date range, company, customer, and sales person

## Installation

```bash
cd ~/frappe-bench
bench get-app sales_person_net_contribution
bench install-app sales_person_net_contribution
bench migrate
```

## Usage

### Automatic Calculation

The app automatically calculates net contribution when:

-   Payment Entry is saved (existing documents only)
-   Payment Entry is submitted

### Manual Calculation

1. Open a submitted Payment Entry (payment_type = "Receive")
2. Click the green button **"تحديث نسبة المندوب"** (Update Sales Person Rate)
3. View calculation results in the success message

### Viewing Results

-   Check Sales Invoice → Sales Team table for updated commission rates
-   Check Payment Entry → References table for calculated custom fields
-   Run Sales Commission Report for aggregated data

## Custom Fields Added

### Payment Entry Reference

-   `custom_tax_amount_from_allocated` - Tax amount from allocated amount
-   `custom_net_without_tax` - Net amount without tax
-   `custom_net_without_tax_without_deductions` - Final net amount after all deductions

### Sales Team

-   `custom_payment_entry` - Link to Payment Entry
-   `custom_date` - Payment Entry date

## API

### Whitelisted Method

```python
calculate_net_contribution(payment_entry_name)
```

Calculates net contribution and updates Sales Invoice Sales Team.

**Parameters:**

-   `payment_entry_name` (str): Payment Entry document name

**Returns:**

-   Status, message, and calculated values

## Workflow

1. **Payment Entry Created** → User creates Payment Entry with references
2. **Validation** → App validates payment_type and references
3. **Analysis** → App analyzes references and determines case type
4. **Calculation** → App calculates deductions and net paid amounts
5. **Update** → App updates Sales Invoice Sales Team with commission data
6. **Result** → User sees success message with calculation details

## Requirements

-   Frappe Framework
-   ERPNext
-   Python 3.10+
-   MariaDB/MySQL

## Configuration

No additional configuration required. The app works out of the box with default ERPNext setup.

## Support

For issues or questions, contact: abdopcnet@gmail.com

## License

MIT License - See `license.txt` for details
