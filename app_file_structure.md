# File Structure - Sales Person Net Contribution

```
sales_person_net_contribution/
├── sales_person_net_contribution/
│   ├── __init__.py                          # App initialization
│   ├── hooks.py                              # Frappe hooks configuration
│   ├── modules.txt                           # App modules
│   ├── patches.txt                           # Database patches
│   │
│   ├── sales_person_net_contribution/
│   │   ├── __init__.py                       # Package initialization
│   │   │
│   │   ├── payment_entry.py                  # Main calculation logic (1290 lines)
│   │   │   ├── Field Validation Functions
│   │   │   ├── Reference Analysis Functions
│   │   │   ├── Deduction Distribution Functions
│   │   │   ├── Invoice Processing Functions
│   │   │   ├── Sales Team Update Functions
│   │   │   ├── Main Calculation Function (@frappe.whitelist)
│   │   │   └── Hook Functions (on_validate, on_submit, on_cancel)
│   │   │
│   │   ├── custom/                           # Custom field definitions
│   │   │   ├── payment_entry_reference.json  # Custom fields for Payment Entry Reference
│   │   │   └── sales_team.json               # Custom fields for Sales Team
│   │   │
│   │   └── report/
│   │       └── sales_commission/             # Sales Commission Report
│   │           ├── __init__.py
│   │           ├── sales_commission.py       # Report logic (SQL queries)
│   │           ├── sales_commission.js         # Report client script
│   │           └── sales_commission.json     # Report definition
│   │
│   └── public/
│       └── js/
│           ├── payment_entry.js              # Payment Entry client script
│           │   ├── Form refresh handler
│           │   ├── Reference field calculations
│   │   ├── Deduction field calculations
│   │   └── Calculate net contribution button
│           │
│           └── payment_entry_list.js         # Payment Entry list view script
│
├── app_api_tree.md                          # API structure documentation
├── app_file_structure.md                    # This file
├── app_workflow.md                          # Workflow diagram
├── app_plan.md                              # Progress tracking
├── README.md                                # App features
├── license.txt                              # License file
├── pyproject.toml                           # Python project config
└── .gitignore                               # Git ignore rules

```

## Key Files Description

### Backend (Python)

**payment_entry.py** (1290 lines)

-   Main business logic for net contribution calculation
-   Handles all three cases: single invoice, single invoice multiple rows, multiple invoices
-   Updates Sales Invoice Sales Team with calculated commission
-   Contains whitelisted API method `calculate_net_contribution`

**report/sales_commission/sales_commission.py**

-   SQL-based report for sales commission tracking
-   Aggregates payment data per invoice
-   Shows sales person, commission rates, paid amounts, deductions

### Frontend (JavaScript)

**public/js/payment_entry.js** (266 lines)

-   Client-side form handlers
-   Real-time calculation of custom fields in references table
-   Button to trigger net contribution calculation
-   Handles deduction changes and reference updates

**public/js/payment_entry_list.js** (204 lines)

-   List view enhancements for Payment Entry

### Configuration

**hooks.py**

-   DocType event hooks (validate, submit, cancel)
-   JavaScript file includes
-   DocType class overrides

**custom/** (JSON files)

-   Custom field definitions for:
    -   Payment Entry Reference table (custom_tax_amount_from_allocated, custom_net_without_tax, etc.)
    -   Sales Team table (custom_payment_entry, custom_date)
