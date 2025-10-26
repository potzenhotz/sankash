# Sankash Architecture

## Functional Design Philosophy

This project embraces **functional programming principles** while working within Reflex's object-oriented framework.

### Core Principles

1. **No Global State**
   - Settings loaded on-demand via `load_settings()`
   - Database path passed explicitly to all service functions
   - No module-level mutable state

2. **Pure Functions First**
   - Service layer functions are pure where possible
   - Return new data structures rather than mutating
   - Polars DataFrames for immutable data pipelines

3. **Side Effects Isolated**
   - Database writes clearly separated from reads
   - Functions named to indicate side effects:
     - `get_*` / `calculate_*` - pure, read-only
     - `create_*` / `update_*` / `delete_*` - side effects

4. **Explicit Dependencies**
   - All functions receive dependencies as parameters
   - Example: `get_transactions(db_path, filters)` not `get_transactions(filters)`

## Architecture Layers

```
┌─────────────────────────────────────────┐
│         Reflex UI Layer (OOP)           │
│  Pages + Components + State Classes     │
└─────────────┬───────────────────────────┘
              │ calls
┌─────────────▼───────────────────────────┐
│      Service Layer (Functional)         │
│   Pure business logic functions         │
│   - transaction_service.py              │
│   - rule_service.py                     │
│   - account_service.py                  │
│   - import_service.py                   │
│   - analytics_service.py                │
└─────────────┬───────────────────────────┘
              │ uses
┌─────────────▼───────────────────────────┐
│     Core Layer (Functional)             │
│   - database.py (connection mgmt)       │
│   - models.py (Pydantic schemas)        │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│          DuckDB Database                │
└─────────────────────────────────────────┘
```

## Service Layer Examples

### Pure Functions (Read-Only)

```python
# Returns new DataFrame, no side effects
def get_transactions(
    db_path: str,
    account_id: Optional[int] = None,
    start_date: Optional[date] = None,
) -> pl.DataFrame:
    query = "SELECT * FROM transactions WHERE 1=1"
    # Build query...
    return execute_query(db_path, query, params)

# Pure computation
def calculate_income_expense(df: pl.DataFrame) -> dict[str, float]:
    income = df.filter(pl.col("amount") > 0)["amount"].sum()
    expense = df.filter(pl.col("amount") < 0)["amount"].sum()
    return {"income": float(income), "expense": float(expense)}
```

### Side Effect Functions (Writes)

```python
# Clearly named to indicate side effect
def create_transaction(db_path: str, transaction: Transaction) -> int:
    result = execute_query(db_path, INSERT_QUERY, transaction.model_dump())
    return int(result["id"][0])

def update_transaction_category(
    db_path: str,
    transaction_id: int,
    category: str,
) -> None:
    execute_command(db_path, UPDATE_QUERY, {"id": transaction_id, "category": category})
```

### Higher-Order Functions (Rule Engine)

```python
# Returns a function (closure)
def create_condition_evaluator(condition: RuleCondition) -> Callable[[Transaction], bool]:
    field = condition.field
    operator = condition.operator
    value = condition.value

    def evaluator(transaction: Transaction) -> bool:
        # Evaluation logic
        return matches

    return evaluator

# Compose evaluators
def evaluate_rule(rule: Rule, transaction: Transaction) -> bool:
    evaluators = [create_condition_evaluator(cond) for cond in rule.conditions]
    return all(evaluator(transaction) for evaluator in evaluators)
```

## Data Flow

### Transaction Import Pipeline (Functional Composition)

```python
# 1. Parse CSV -> DataFrame
df = parse_csv_to_dataframe(file_path)

# 2. Transform -> add metadata
df = transform_import_dataframe(df, account_id)

# 3. Filter -> remove duplicates
new_df, dups = filter_duplicate_transactions(df, existing_df)

# 4. Import -> side effect (isolated at the end)
for row in new_df.to_dicts():
    create_transaction(db_path, Transaction(**row))
```

### Rule Application Pipeline

```python
# 1. Get rules and transactions (pure)
rules = get_rules(db_path)
transactions = get_transactions(db_path, is_categorized=False)

# 2. Evaluate (pure)
for tx in transactions:
    matching_rule = find_first(lambda r: evaluate_rule(r, tx), rules)

    # 3. Apply side effect (isolated)
    if matching_rule:
        apply_rule_actions(db_path, matching_rule, tx.id)
```

## Testing Strategy

- **Unit tests** for pure functions (easy - no mocks needed)
- **Integration tests** for side-effect functions (test DB)
- **Property-based tests** for data transformations

## Key Files

### Core Layer
- `sankash/core/database.py` - Connection management, query execution
- `sankash/core/models.py` - Pydantic models for type safety
- `sankash/core/schema.sql` - Database DDL

### Service Layer (Pure Functions)
- `sankash/services/transaction_service.py` - Transaction CRUD
- `sankash/services/rule_service.py` - Rule engine (higher-order functions)
- `sankash/services/import_service.py` - CSV import pipeline
- `sankash/services/analytics_service.py` - Dashboard calculations
- `sankash/services/account_service.py` - Account management
- `sankash/services/category_service.py` - Category operations

### Utils (Pure Functions)
- `sankash/utils/formatters.py` - Display formatting
- `sankash/utils/validators.py` - Input validation
- `sankash/utils/duplicate_detection.py` - Duplicate logic

### Config
- `config/settings.py` - Settings loader (no globals)
- `config/settings.yaml` - User configuration

## Benefits of This Approach

1. **Testability** - Pure functions easy to test, no mocks
2. **Composability** - Functions combine cleanly
3. **Predictability** - Same inputs → same outputs
4. **Refactoring** - Side effects isolated, safe to refactor pure logic
5. **Concurrency** - Pure functions thread-safe by default
6. **Debugging** - Easier to reason about data flow

## Trade-offs

- **More parameters** - `db_path` passed everywhere (but explicit is better)
- **Less convenient** - Can't just import and call, need to wire dependencies
- **Mixed paradigms** - Reflex state classes are OOP (unavoidable)

## Next Steps

The functional core is complete. UI layer will use Reflex's OOP patterns but will call into the pure functional service layer, keeping business logic clean and testable.
