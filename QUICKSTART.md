# Sankash Quickstart Guide

Get up and running with Sankash in 5 minutes!

> **⚠️ IMPORTANT: Run the setup script first!**
>
> Before starting the app, you **must** run `python scripts/setup.py` to initialize the database.
> Otherwise you'll see errors like "Table with name accounts does not exist!"

## Prerequisites

- Python 3.11 or higher

## Quick Setup (3 Commands)

```bash
# 1. Install dependencies
uv install

# 2. Initialize database (REQUIRED!)
uv run scripts/setup.py

# 3. Start the app
uv run reflex run
```

**What setup.py does:**

- Creates the `sankash.duckdb` database file
- Initializes all tables (accounts, transactions, categories, rules)
- Creates indexes for performance
- Seeds 12 default categories (Groceries, Dining, etc.)

**You'll see output like:**

```
🚀 Setting up Sankash...

📊 Initializing database at: sankash.duckdb
✅ Database initialized

🏷️  Seeding default categories...
✅ Default categories created

✨ Setup complete!
```

### 5. Start the app

```bash
uv run reflex run
```

The app will open at `http://localhost:3000` (or the next available port if 3000 is taken)

## Configuration (Optional)

### Settings File

Sankash can be customized via a settings file located at `config/settings.yaml`.

**Location:** `config/settings.yaml`

**How to create:**

```bash
# Copy the example file
cp config/settings.example.yaml config/settings.yaml

# Edit with your preferences
nano config/settings.yaml  # or your favorite editor
```

**Available Settings:**

```yaml
# Database file location
db_path: "sankash.duckdb"

# Default currency for new accounts
default_currency: "EUR"  # Options: EUR, USD, GBP

# Date format for imports and display
date_format: "%Y-%m-%d"

# Number of transactions to process at once during import
import_chunk_size: 1000
```

### How Settings Work with setup.py

When you run `uv run python scripts/setup.py`:

1. **Looks for** `config/settings.yaml`
2. **If found:** Uses your custom settings (especially `db_path`)
3. **If not found:** Uses defaults (shown above)
4. **Creates database** at the location specified by `db_path`

**Example - Custom Database Location:**

```yaml
# config/settings.yaml
db_path: "/Users/you/finance-data/sankash.duckdb"
default_currency: "USD"
```

Then running setup will create the database at your custom location:

```bash
uv run python scripts/setup.py
# Output: 📊 Initializing database at: /Users/you/finance-data/sankash.duckdb
```

**Note:** Settings file is completely optional! The defaults work great for most users. Only create `settings.yaml` if you need to customize the database location or default currency.

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

Sankash supports importing from **Standard CSV**, **Deutsche Bank**, or **ING** bank exports.

#### Option A: Standard CSV Format

Prepare a CSV with these columns:

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

#### Option B: Bank Export Files

You can directly import raw exports from:

- **Deutsche Bank**: Semicolon-separated, German decimal format (comma), date format DD.MM.YYYY
- **ING**: Semicolon-separated with metadata rows, German number format (1.234,56)

The app automatically converts these formats to the standard format.

#### Import Process

1. Go to **Import** page
2. Select your account
3. **Select bank format**:
   - "Standard CSV" for pre-formatted files
   - "Deutsche Bank" for Deutsche Bank exports
   - "ING" for ING bank exports
4. Upload CSV file
5. Click "Preview" to verify data
6. Click "Import" to import transactions

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

### ❌ "Table with name accounts does not exist!"

This is the most common error - it means you haven't initialized the database yet.

**Solution:**

```bash
# Stop the app (Ctrl+C if running)
# Run the setup script
python scripts/setup.py

# Start the app again
reflex run
```

The setup script **must** be run before first use!

---

### Database not found or corrupted

```bash
# Delete and recreate database
rm sankash.duckdb
python scripts/setup.py
```

### Import fails

- Check CSV format (date, payee, notes, amount)
- Ensure dates are YYYY-MM-DD
- Verify account is selected
- Check file is UTF-8 encoded

### Rules not applying

- Check rule is active (green badge)
- Test rule with "Test" button
- Check priority order
- Verify condition matches payee format

Happy budgeting! 💰
