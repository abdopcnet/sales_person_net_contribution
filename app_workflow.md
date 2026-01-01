# Workflow Diagram - Sales Person Net Contribution

## Main Calculation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Payment Entry Created                    │
│              (payment_type = "Receive")                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │   on_validate Hook Triggered │
         │   (Skip if new document)     │
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  calculate_net_contribution  │
         │      (API Method Call)       │
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │   Validate Payment Entry    │
         │  - payment_type = "Receive" │
         │  - references exist         │
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Analyze References Table   │
         │  - Group by invoice         │
         │  - Determine case type       │
         └──────────────┬────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
    ┌─────────┐              ┌──────────────┐
    │ Case 1: │              │ Case 2 & 3:  │
    │ Single  │              │ Multiple     │
    │ Invoice │              │ Invoices     │
    └────┬────┘              └──────┬───────┘
         │                           │
         └─────────────┬─────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Calculate Total Deductions │
         │  (Sum from deductions table)│
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ Distribute Deductions       │
         │ (Proportional by allocated) │
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Process Each Invoice       │
         │  ┌───────────────────────┐  │
         │  │ 1. Get Sales Team    │  │
         │  │    (Invoice → Order)  │  │
         │  │ 2. Calculate Net Paid │  │
         │  │ 3. Calculate Incentives│ │
         │  │ 4. Update Sales Team │  │
         │  └───────────────────────┘  │
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Update Sales Invoice       │
         │  - Save Sales Team changes │
         │  - Update custom fields    │
         └──────────────┬────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Return Success Message     │
         │  (With calculation details) │
         └─────────────────────────────┘
```

## Case Types

### Case 1: Single Invoice

```
Payment Entry References:
┌─────────────────────────────┐
│ Sales Invoice: INV-001      │
│ Allocated: 1000             │
└─────────────────────────────┘
→ Process single invoice directly
```

### Case 2: Single Invoice, Multiple Rows

```
Payment Entry References:
┌─────────────────────────────┐
│ Sales Invoice: INV-001      │
│ Allocated: 500              │
├─────────────────────────────┤
│ Sales Invoice: INV-001      │
│ Allocated: 500              │
└─────────────────────────────┘
→ Aggregate amounts (1000 total)
→ Process as single invoice
```

### Case 3: Multiple Invoices

```
Payment Entry References:
┌─────────────────────────────┐
│ Sales Invoice: INV-001      │
│ Allocated: 600              │
├─────────────────────────────┤
│ Sales Invoice: INV-002      │
│ Allocated: 400              │
└─────────────────────────────┘
→ Distribute deductions proportionally
→ Process each invoice separately
```

## Sales Team Update Flow

```
┌─────────────────────────────┐
│   Get Sales Team            │
│   Priority 1: From Invoice  │
│   Priority 2: From Order     │
└──────────────┬────────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Calculate Net Paid        │
│   = Allocated - Deductions  │
└──────────────┬────────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Calculate Incentives     │
│   = Net Paid × Rate        │
└──────────────┬────────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Update Sales Team Table   │
│   - Add/Update row          │
│   - Set custom_payment_entry│
│   - Set custom_date         │
│   - Update incentives       │
└──────────────┬────────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Save Sales Invoice        │
└─────────────────────────────┘
```

## Hook Events Flow

```
┌─────────────────────────────────────┐
│         Payment Entry Save          │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │   on_validate Hook    │
    │  (if not new doc)     │
    └──────────┬─────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Auto-calculate Net  │
    │     Contribution     │
    └──────────────────────┘

┌─────────────────────────────────────┐
│      Payment Entry Submit            │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │   on_submit Hook     │
    └──────────┬────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Auto-calculate Net  │
    │     Contribution     │
    └──────────────────────┘

┌─────────────────────────────────────┐
│      Payment Entry Cancel            │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │   on_cancel Hook     │
    └──────────┬────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Remove Sales Team   │
    │  Payment Entry Refs  │
    └──────────────────────┘
```

## Client-Side Calculation Flow

```
┌─────────────────────────────┐
│   Payment Entry Form Open   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   refresh Event Triggered    │
│   - Calculate reference fields│
│   - Show "تحديث نسبة المندوب"│
│     button (if submitted)    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   User Changes:              │
│   - allocated_amount         │
│   - deductions.amount       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Auto-calculate Fields:    │
│   - custom_tax_amount        │
│   - custom_net_without_tax  │
│   - custom_net_without_...  │
└─────────────────────────────┘
```
