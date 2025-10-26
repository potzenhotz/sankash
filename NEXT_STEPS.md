# Next Steps - Start Using Sankash

## ⚡ Quick Start (5 minutes)

### 1. Install and Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run setup (creates database, seeds categories)
python scripts/setup.py

# Start the app
reflex run
```

The app will open at `http://localhost:3000`

### 2. First-Time Configuration

Create `config/settings.yaml` (optional):

```bash
cp config/settings.example.yaml config/settings.yaml
```

Edit if needed (defaults are fine):
```yaml
db_path: "sankash.duckdb"
default_currency: "EUR"
date_format: "%Y-%m-%d"
import_chunk_size: 1000
```

## 📋 Initial Setup Checklist

### In the Application

1. **Create Your First Account** (Accounts page)
   - [ ] Name: e.g., "Main Checking"
   - [ ] Bank: e.g., "Deutsche Bank"
   - [ ] Account Number
   - [ ] Currency: EUR/USD/GBP

2. **Prepare Your CSV** (see format below)
   - [ ] Export from your bank
   - [ ] Convert to standard format (or create converter)

3. **Import Transactions** (Import page)
   - [ ] Select account
   - [ ] Upload CSV
   - [ ] Preview
   - [ ] Import

4. **Create Rules** (Rules page)
   - [ ] Create rule for common payees
   - [ ] Example: "Grocery" → "Groceries"
   - [ ] Test rule
   - [ ] Apply to uncategorized

5. **View Dashboard**
   - [ ] Check KPIs
   - [ ] Review spending

## 📁 CSV Format

Your bank CSV should be converted to this format:

```csv
date,payee,notes,amount
2024-01-15,REWE Supermarket,Weekly groceries,-45.50
2024-01-16,Employer Inc,Monthly salary,3000.00
2024-01-17,Starbucks,Morning coffee,-4.20
2024-01-18,Amazon.de,Book purchase,-19.99
```

**Requirements:**
- `date`: YYYY-MM-DD format
- `payee`: Transaction description
- `notes`: Optional additional info
- `amount`: Negative for expenses, positive for income

## 🏦 Create Bank Converters

You mentioned Deutsche Bank and ING. Here's how to create converters:

### Example: Deutsche Bank Converter

Create `converters/deutsche_bank.py`:

```python
"""Deutsche Bank CSV converter."""

from pathlib import Path
import polars as pl


def convert_deutsche_bank_csv(file_path: str | Path) -> pl.DataFrame:
    """
    Convert Deutsche Bank CSV to standard format.

    Adjust column names based on your bank's format.
    """
    df = pl.read_csv(file_path, separator=";")  # Deutsche Bank uses semicolon

    # Map Deutsche Bank columns to standard format
    # Adjust these based on actual column names
    df = df.rename({
        "Buchungstag": "date",
        "Buchungstext": "payee",
        "Verwendungszweck": "notes",
        "Betrag": "amount",
    })

    # Convert date format if needed
    df = df.with_columns([
        pl.col("date").str.strptime(pl.Date, format="%d.%m.%Y"),
        pl.col("amount").str.replace(",", ".").cast(pl.Float64),
    ])

    # Select only needed columns
    return df.select(["date", "payee", "notes", "amount"])
```

### Usage

```python
from converters.deutsche_bank import convert_deutsche_bank_csv
from sankash.services.import_service import import_transactions
from config.settings import load_settings

settings = load_settings()

# Import with converter
stats = import_transactions(
    settings.db_path,
    "path/to/deutsche_bank_export.csv",
    account_id=1,
    converter=convert_deutsche_bank_csv,  # Pass converter function
)
```

Or integrate into UI by modifying `import_state.py` to detect bank type.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sankash tests/

# Run specific test file
pytest tests/test_services/test_rule_service.py -v
```

## 📊 Sample Data

Want to test with sample data? Create `sample_transactions.csv`:

```csv
date,payee,notes,amount
2024-01-01,Employer,Salary,3000.00
2024-01-02,REWE,Groceries,-85.50
2024-01-03,Shell,Gas,-45.00
2024-01-04,Netflix,Subscription,-12.99
2024-01-05,Restaurant Milano,Dinner,-67.80
2024-01-06,Amazon,Books,-34.99
2024-01-07,Lidl,Groceries,-52.30
2024-01-08,Gym Membership,Monthly fee,-49.90
2024-01-09,Freelance Client,Project payment,1500.00
2024-01-10,Spotify,Subscription,-9.99
```

Import this to get started!

## 🎯 Common Workflows

### Monthly Routine

```bash
1. Export transactions from bank
2. Convert to standard CSV (or use converter)
3. Import via UI
4. Review auto-categorized transactions
5. Manually categorize remaining
6. Create new rules for recurring merchants
7. View dashboard for insights
```

### Creating Effective Rules

**Good Rule Examples:**

```
Name: Grocery Auto-categorize
Condition: payee contains "REWE"
Action: set_category → "Groceries"
Priority: 10
```

```
Name: Salary Income
Condition: payee contains "Employer Inc"
Action: set_category → "Salary"
Priority: 10
```

```
Name: Large Purchases
Condition: amount < -500
Action: set_category → "Large Purchase"
Priority: 5
```

**Rule Tips:**
- Use higher priority (10) for specific rules
- Use lower priority (5) for general rules
- Test rules before activating
- Create rule from transaction shortcut

## 🐛 Troubleshooting

### Database Issues

```bash
# Reset database
rm sankash.duckdb
python scripts/setup.py
```

### Import Errors

- Check CSV encoding (should be UTF-8)
- Verify date format is YYYY-MM-DD
- Ensure amount is numeric (use . for decimal)
- Check column names match exactly

### Reflex Not Starting

```bash
# Reinstall dependencies
pip install -e ".[dev]" --force-reinstall

# Clear Reflex cache
rm -rf .web
reflex init
reflex run
```

## 📚 Documentation Reference

- **QUICKSTART.md** - User guide and examples
- **ARCHITECTURE.md** - Technical design and patterns
- **PROJECT_SUMMARY.md** - Feature overview and statistics
- **README.md** - Project overview

## 🚀 Optional Enhancements

Once you're comfortable, consider:

1. **Plotly Sankey Diagram** - Visualize money flow
2. **Category Management UI** - Add/edit categories via UI
3. **Transfer Detection** - Link transfers between accounts
4. **Budget Goals** - Set spending limits per category
5. **Recurring Detection** - Highlight recurring transactions
6. **Export Reports** - PDF/Excel export functionality

## 💡 Pro Tips

1. **Bulk Categorization**: Use filters + bulk actions to categorize many at once
2. **Rule Testing**: Always test rules before activating
3. **Backup Database**: Copy `sankash.duckdb` periodically
4. **Category Hierarchy**: Use parent categories for better organization
5. **Import Regularly**: Monthly imports keep data fresh

## 🤝 Contributing

If you extend Sankash:
- Add bank converters to `converters/`
- Write tests for new features
- Follow functional programming patterns
- Update documentation

## 📞 Need Help?

Check the docs:
- Service layer examples in `sankash/services/`
- Test examples in `tests/`
- UI patterns in `sankash/pages/`

---

**You're all set! Start with `python scripts/setup.py` and `reflex run`** 🎉

Happy budgeting! 💰
