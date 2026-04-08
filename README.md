# Sankash - Personal Finance Budget Tracker

A modern personal finance app built with Reflex, Polars, and Plotly.

## Features

- Multi-account transaction management
- Automatic categorization using rules
- Interactive Sankey diagram dashboard
- CSV import with duplicate detection
- Transfer tracking between accounts

## Tech Stack

- **Reflex** - Python web framework
- **Polars** - Fast DataFrame operations
- **Plotly** - Interactive visualizations
- **Pydantic** - Data validation

## Architecture

This project follows a **functional-first approach** where possible:

- **Pure functions** for business logic (services, utils)
- **No global state** - settings loaded on demand
- **Immutable data flow** - Polars DataFrames passed through pipelines
- **File-based storage** - no database, no migrations

### Data Storage

All data lives in the `data/` directory as plain files:

```
data/
  transactions.parquet          # Raw imports, append-only
  transaction_overrides.json    # Per-transaction edits (categories, transfers)
  import_history.json           # Import tracking and file hashes
  config/
    accounts.yaml               # Account definitions
    categories.yaml             # Category hierarchy
    rules.yaml                  # Categorization rules
    app_settings.yaml           # Runtime settings
```

- **Parquet** for transactions (typed, compressed, Polars-native)
- **YAML** for config data (human-readable, version-controllable)
- **JSON** for structured runtime data

Transactions are append-only. Categorization and other edits go into `transaction_overrides.json`, which is merged at read time. This means re-importing CSVs never overwrites your categorization work.

### Directory Structure

```
sankash/
  config/              # Application settings (YAML-based)
  sankash/
    core/              # Storage layer and data models
    services/          # Business logic (pure functions)
    utils/             # Helper functions (pure)
    pages/             # Reflex pages/routes
    components/        # Reusable UI components
    state/             # Reflex state management (OOP)
  converters/          # Bank CSV converters
  scripts/             # Utility scripts
  tests/               # Test suite
```

### Key Design Principles

1. **Explicit dependencies** - All functions receive their dependencies as parameters (e.g., `data_dir`)
2. **Pure functions** - Services return new data without side effects where possible
3. **Separation of concerns** - Storage, business logic, and UI are decoupled
4. **Type safety** - Pydantic models for data validation
5. **No migrations** - File-based storage evolves naturally with the code

## Setup

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Create configuration:
```bash
cp config/settings.example.yaml config/settings.yaml
# Edit settings.yaml with your preferences
```

3. Initialize data directory:
```bash
python scripts/setup.py
```

4. Run the app:
```bash
reflex run
```

## Usage

### Import Transactions

Place your CSV files in a known location and use the Import page to upload them.

### Create Rules

Define rules to automatically categorize transactions based on payee, amount, or notes.

### View Dashboard

Explore your spending with interactive Sankey diagrams and charts.

## Development

Run tests:
```bash
pytest
```

Type checking:
```bash
mypy sankash
```

Linting:
```bash
ruff check sankash
```

## License

MIT
