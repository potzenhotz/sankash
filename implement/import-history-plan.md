# Implementation Plan - CSV Import History Feature
**Created:** 2025-12-30
**Feature:** Import history tracking with source file visibility in transactions

## Source Analysis
- **Source Type:** Feature Request
- **Core Features:**
  - Track which CSV files have been imported
  - Show import history in import page
  - Display import source for each transaction
  - Prevent re-importing the same file
  - Visual indication of which transactions came from which CSV
- **Dependencies:** None (all existing: Reflex, Polars, DuckDB)
- **Complexity:** Medium - Database schema changes, UI updates, service modifications

## Current State Analysis

**Database Schema (schema.sql:29-45):**
- ✅ Transactions table has `imported_id` field (for duplicate detection)
- ❌ No table to track import history/metadata
- ❌ No link between transactions and source file

**Import Service (import_service.py):**
- ✅ Creates unique `imported_id` for each transaction
- ✅ Handles duplicate detection
- ✅ Returns import statistics
- ❌ Doesn't track import file metadata (filename, date, count)
- ❌ Doesn't store import session information

**Import Page (import_page.py):**
- ✅ Shows preview and results
- ❌ No history display
- ❌ No visual indication of previous imports

**Transaction Page (transactions.py):**
- ✅ Shows transaction details
- ❌ Doesn't show import source

## Target Integration

### Database Changes:
1. Create `import_history` table to track each import session
2. Add `import_session_id` foreign key to transactions table

### New/Modified Files:

**Database Schema:**
1. `sankash/core/schema.sql` - Add import_history table and modify transactions

**Models:**
2. `sankash/core/models.py` - Add ImportHistory model

**Services:**
3. `sankash/services/import_service.py` - Track import sessions
4. Create `sankash/services/import_history_service.py` - CRUD for import history

**State:**
5. `sankash/state/import_state.py` - Add history loading and display

**Pages:**
6. `sankash/pages/import_page.py` - Add history section
7. `sankash/pages/transactions.py` - Add import source column

## Implementation Tasks

### Phase 1: Database Schema Updates
- [ ] Create `import_history` table with:
  - id (primary key)
  - filename (original CSV filename)
  - account_id (foreign key to accounts)
  - bank_format (which format was used)
  - import_date (timestamp)
  - total_count (total records in file)
  - imported_count (successfully imported)
  - duplicate_count (skipped duplicates)
  - categorized_count (auto-categorized)
  - file_hash (optional - to detect identical files)
- [ ] Add `import_session_id` column to transactions table (nullable for legacy)
- [ ] Create index on transactions.import_session_id
- [ ] Create migration script or handle schema updates gracefully

### Phase 2: Data Models
- [ ] Add `ImportHistory` model in models.py
- [ ] Update `Transaction` model to include import_session_id field
- [ ] Add computed var for import source display

### Phase 3: Import History Service
- [ ] Create `import_history_service.py`
- [ ] Add `create_import_history()` function
- [ ] Add `get_import_history()` function (with filtering by account)
- [ ] Add `get_import_by_id()` function
- [ ] Add `delete_import_history()` function (optional - for cleanup)
- [ ] Add helper to compute file hash for duplicate file detection

### Phase 4: Update Import Service
- [ ] Modify `import_transactions()` to:
  - Calculate file hash before import
  - Check if identical file already imported (optional warning)
  - Create import_history record before importing transactions
  - Pass import_session_id when creating transactions
  - Update import_history with final stats
- [ ] Update `create_transaction()` to accept import_session_id
- [ ] Ensure backward compatibility for existing transactions

### Phase 5: Import State Updates
- [ ] Add import_history list to ImportState
- [ ] Add `load_import_history()` method
- [ ] Add pagination/limit for history (show last 20 imports)
- [ ] Add computed var for formatted history display
- [ ] Add warning if trying to import duplicate file

### Phase 6: Import Page UI - History Section
- [ ] Add import history section below results
- [ ] Show history as table or cards with:
  - Filename
  - Import date
  - Account name
  - Statistics (total, imported, duplicates, categorized)
  - Bank format used
- [ ] Add expand/collapse functionality
- [ ] Add "View Transactions" button to filter transactions by import
- [ ] Optional: Add delete button for import history cleanup

### Phase 7: Transaction Page Updates
- [ ] Add "Import Source" column to transactions table
- [ ] Show import filename and date for each transaction
- [ ] Add filter by import source
- [ ] Add badge or icon to indicate imported transactions
- [ ] Show "-" for manually created transactions

### Phase 8: Transaction Service Updates
- [ ] Modify `get_transactions()` to join with import_history
- [ ] Add import source fields to transaction query results
- [ ] Update transaction state to include import metadata

### Phase 9: Testing & Validation
- [ ] Test fresh import creates history record
- [ ] Test transactions linked to import session
- [ ] Test duplicate file detection
- [ ] Test history display in import page
- [ ] Test import source display in transactions
- [ ] Test filtering transactions by import
- [ ] Test backward compatibility with existing transactions

## Validation Checklist
- [ ] Import history table created successfully
- [ ] New imports create history records
- [ ] Transactions linked to import sessions
- [ ] Import history visible in import page
- [ ] Import source visible in transaction table
- [ ] Can filter transactions by import source
- [ ] Duplicate file detection works (if implemented)
- [ ] Legacy transactions (no import_session_id) display correctly
- [ ] Statistics accurate in history
- [ ] No performance degradation
- [ ] App compiles with no warnings

## Database Schema Design

### import_history table:
```sql
CREATE TABLE IF NOT EXISTS import_history (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_import_history_id'),
    filename VARCHAR NOT NULL,
    account_id INTEGER NOT NULL,
    bank_format VARCHAR NOT NULL,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_count INTEGER NOT NULL,
    imported_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    categorized_count INTEGER NOT NULL,
    file_hash VARCHAR,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

### transactions table update:
```sql
ALTER TABLE transactions ADD COLUMN import_session_id INTEGER;
ALTER TABLE transactions ADD CONSTRAINT fk_import_session
    FOREIGN KEY (import_session_id) REFERENCES import_history(id);
CREATE INDEX IF NOT EXISTS idx_transactions_import_session ON transactions(import_session_id);
```

## Risk Mitigation
- **Potential Issues:**
  - Backward compatibility with existing transactions (no import_session_id)
  - Database migration handling
  - Performance with large import history
  - File hash computation for large files

- **Solutions:**
  - Make import_session_id nullable
  - Gracefully handle null import sources in UI
  - Add pagination/limit to history queries
  - Optional file hash (can skip for MVP)

- **Rollback Strategy:**
  - New columns are nullable (won't break existing data)
  - Can drop import_history table if needed
  - Git checkpoint after each phase
  - Feature is additive (no breaking changes to existing functionality)

## Architecture Decisions
1. **Use import_session_id in transactions** - Clean foreign key relationship
2. **Store filename + metadata** - Track what was imported when
3. **Optional file hash** - Can add later for duplicate file detection
4. **Backward compatible** - Legacy transactions work without import_session_id
5. **Show in both places** - Import page shows history, transactions show source
6. **Keep statistics** - Track import success rates and duplicates

## Expected Outcome
- Complete import history tracking
- Visual history in import page showing all past imports
- Each transaction shows which CSV it came from
- Better audit trail for imported data
- Prevent accidental duplicate imports
- Foundation for advanced import analytics
