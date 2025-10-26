# Sankash Quickstart Guide

Get up and running with Sankash in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- pip

## Installation

1. **Clone or navigate to the project**

```bash
cd sankash
```

2. **Create virtual environment (recommended)**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -e ".[dev]"
```

4. **Run setup script**

```bash
python scripts/setup.py
```

This will:
- Create the database file
- Initialize the schema
- Seed default categories

5. **Start the app**

```bash
reflex run
```

The app will open at `http://localhost:3000`

## First Steps

### 1. Create an Account

- Navigate to **Accounts** page
- Click "Add New Account"
- Fill in:
  - Account Name (e.g., "Main Checking")
  - Bank Name (e.g., "Deutsche Bank")
  - Account Number
  - Currency (EUR, USD, or GBP)
- Click "Create Account"

### 2. Import Transactions

#### Prepare Your CSV

Your CSV should have these columns:
```csv
date,payee,notes,amount
2024-01-15,Grocery Store,Weekly shopping,-45.50
2024-01-16,Salary,Monthly salary,3000.00
2024-01-17,Coffee Shop,Morning coffee,-4.20
```

**Format requirements:**
- `date`: YYYY-MM-DD
- `payee`: Transaction description
- `notes`: Optional notes
- `amount`: Negative for expenses, positive for income

#### Import Process

- Go to **Import** page
- Select your account
- Upload CSV file
- Click "Preview" to verify data
- Click "Import" to import transactions

### 3. Categorize Transactions

#### Manual Categorization

- Go to **Transactions** page
- Find uncategorized transactions
- Select category from dropdown
- Or select multiple and use bulk actions

#### Automatic with Rules

- Go to **Rules** page
- Create a rule:
  - Name: "Grocery Categorization"
  - Condition: `payee` `contains` `grocery`
  - Action: `set_category` → `Groceries`
  - Priority: 10
- Click "Create Rule"
- Click "Apply Rules to Uncategorized"

Future imports will auto-categorize!

### 4. View Dashboard

- Go to **Dashboard** page
- See your financial overview:
  - Income/Expense/Net KPIs
  - Uncategorized transaction count
  - Money flow visualization (Sankey diagram - coming soon)
- Use time period filters (Last Month/Quarter/Year)

## Example Workflow

```bash
# 1. Setup
python scripts/setup.py

# 2. Start app
reflex run

# 3. In browser (http://localhost:3000)
# → Create account "Main Checking"
# → Import January_Transactions.csv
# → Create rules for common payees
# → Apply rules
# → View dashboard

# 4. Repeat monthly
# → Import new CSV
# → Auto-categorize with existing rules
# → Create new rules as needed
```

## Default Categories

The setup creates these categories:

**Expenses:**
- Groceries
- Dining Out
- Transportation
- Utilities
- Rent
- Healthcare
- Entertainment
- Shopping
- Other

**Income:**
- Income
- Salary (sub-category)
- Investment (sub-category)

## Tips

### Filtering Transactions

Use filters to find specific transactions:
- **Date range**: Last 30 days button or custom dates
- **Amount range**: Min/max amount
- **Uncategorized only**: Focus on transactions needing categories

### Rule Priority

Higher priority rules run first. Use this for:
- Specific rules (priority 10): "Amazon Prime" → "Subscriptions"
- General rules (priority 5): "Amazon" → "Shopping"

### Bulk Operations

1. Apply filters to narrow down transactions
2. Select multiple transactions (checkboxes)
3. Choose category from dropdown
4. Click "Apply to Selected"

## Troubleshooting

**Database not found**
```bash
# Re-run setup
python scripts/setup.py
```

**Import fails**
- Check CSV format (date, payee, notes, amount)
- Ensure dates are YYYY-MM-DD
- Verify account is selected

**Rules not applying**
- Check rule is active (green badge)
- Test rule with "Test" button
- Check priority order
- Verify condition matches payee format

## Configuration

Edit `config/settings.yaml`:

```yaml
db_path: "sankash.duckdb"
default_currency: "EUR"
date_format: "%Y-%m-%d"
import_chunk_size: 1000
```

Happy budgeting! 💰
