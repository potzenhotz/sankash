# Sankash - Personal Finance Budget Tracker

A personal finance app: import bank CSVs, categorize with rules, see where the money goes in a Sankey diagram. The UI is moving from Reflex to a React frontend (see [Status](#status)).

## Features

- Multi-account transaction management
- Automatic categorization using rules
- Interactive Sankey diagram dashboard
- CSV import with duplicate detection
- Transfer tracking between accounts

## Tech Stack

- **Polars** - DataFrame operations in the service layer
- **Pydantic** - Data validation
- **FastAPI** - JSON API for the new frontend (`sankash/api/`)
- **React + Vite + TypeScript** - new frontend (`web/`), TanStack Query, cmdk, ECharts
- **Reflex + Plotly** - old UI, still used for the pages not ported yet

## Architecture

This project follows a **functional-first approach** where possible:

- **Pure functions** for business logic (services, utils)
- **No global state** - settings loaded on demand
- **Immutable data flow** - Polars DataFrames passed through pipelines
- **File-based storage** - no database

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

Transactions are append-only. Manual categorizations and other edits go into `transaction_overrides.json`, which is merged at read time. This means re-importing CSVs never overwrites your categorization work.

Rule results are never stored: every read derives the category as "manual assignment if present, otherwise the first matching active rule by priority". New or edited rules therefore apply to all transactions immediately, with no "apply" step.

### Directory Structure

```
sankash/
  Taskfile.yml         # task dev / test / build / reflex
  config/              # Application settings (YAML-based)
  sankash/
    api/               # FastAPI app for the React frontend
    core/              # Storage layer and data models
    services/          # Business logic (pure functions), shared by both UIs
    utils/             # Helper functions (pure)
    converters/        # Bank CSV converters
    pages/ components/ state/   # Reflex UI (being replaced)
  web/                 # React frontend (Vite, TypeScript)
    src/dashboard.ts   # Dashboard computations (tested with node:test)
  scripts/             # Utility scripts
  tests/               # Python test suite
```

### Key Design Principles

1. **Explicit dependencies** - All functions receive their dependencies as parameters (e.g., `data_dir`)
2. **Pure functions** - Services return new data without side effects where possible
3. **Separation of concerns** - Storage, business logic, and UI are decoupled
4. **Type safety** - Pydantic models for data validation
5. **Ad-hoc migrations** - schema changes are handled in code on read (e.g. `parent_id` backfill, `migrate_rules_to_category_based`); keep them idempotent

## Setup

Requires [uv](https://docs.astral.sh/uv/), Node.js and [go-task](https://taskfile.dev) (`brew install go-task`).

```bash
uv sync                      # Python dependencies
uv run python scripts/setup.py   # first run only: creates data/
task dev                     # API + React frontend → http://localhost:5173
task reflex                  # old UI → http://localhost:3000 (rules, import, ...)
```

`config/settings.yaml` is optional (copy `config/settings.example.yaml`). A relative `data_dir` is resolved against the project root, so it does not matter which directory you start from.

## Status

### New frontend (in progress)

A React frontend (`web/`) is replacing the Reflex pages one by one. It talks to a FastAPI layer (`sankash/api/`) over the same services. So far it covers:

- **Dashboard**: money-flow Sankey (income categories → accounts → expense categories, click to list transactions), income/expense bars, period/account filters, category exclusion, grouping by parent category
- **Transactions**: keyboard categorization (`Enter` category, `n` rule, `r` reset to rule, `u` uncategorized only, `/` search)

Rules, categories, import, accounts and settings are still in the Reflex app (`task reflex`).

```bash
task dev      # API on :8001 + frontend on http://localhost:5173, Ctrl+C stops both
task          # list all tasks (api, web, reflex, test, build)
```

The Reflex app keeps working alongside it; both read the same `data/` directory.

### Next steps

1. Port the **rules page** (then all categorization lives in the new frontend), then categories, import, accounts, settings
2. Remove the Reflex UI (`sankash/pages`, `components`, `state`, `rxconfig.py`) once everything is ported
3. Generate frontend types from the OpenAPI schema (`openapi-typescript`) instead of the hand-written `web/src/api.ts` once the API grows

### Deferred / known issues

- **Bank sync instead of CSV export**: evaluated FinTS (`python-fints` needs a free product ID from the Deutsche Kreditwirtschaft, 10-15 working days), Enable Banking (free for own accounts, data passes a third party) and MoneyMoney. Deferred; CSV import stays. Watch out: `imported_id` hashes payee/notes text, so a new source would duplicate CSV rows without a cutoff date.
- Rule actions of type `mark_transfer` are not derived at read time (no rule uses them, the UI cannot create them)
- Reflex transactions page shows amounts as `€-550` instead of `-550,00 €`
- Frontend bundle is ~880 KB (mostly ECharts); fine locally, Vite warns on build

## Usage

### Import Transactions

Place your CSV files in a known location and use the Import page to upload them.

### Create Rules

Define rules to automatically categorize transactions based on payee, amount, or notes.

### View Dashboard

Explore your spending in the Sankey diagram; click a category, account or flow to list its transactions.

## Development

```bash
task test                     # pytest + frontend tests + TypeScript typecheck
uv run ruff check sankash     # lint
```

## License

MIT
