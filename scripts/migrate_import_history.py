"""Migration script to add import_history table and import_session_id column."""

import duckdb
from pathlib import Path


def migrate_database(db_path: str) -> None:
    """
    Migrate database to add import history support.

    This script is idempotent - safe to run multiple times.
    """
    print(f"Migrating database: {db_path}")
    con = duckdb.connect(db_path)

    try:
        # Check if import_history table exists
        result = con.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_name = 'import_history'
        """).fetchone()

        if result[0] == 0:
            print("Creating import_history table...")

            # Create sequence
            con.execute("CREATE SEQUENCE IF NOT EXISTS seq_import_history_id START 1")

            # Create import_history table (without foreign key constraint for compatibility)
            con.execute("""
                CREATE TABLE import_history (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_import_history_id'),
                    filename VARCHAR NOT NULL,
                    account_id INTEGER NOT NULL,
                    bank_format VARCHAR NOT NULL,
                    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_count INTEGER NOT NULL,
                    imported_count INTEGER NOT NULL,
                    duplicate_count INTEGER NOT NULL,
                    categorized_count INTEGER NOT NULL,
                    file_hash VARCHAR
                )
            """)

            # Create index
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_import_history_account_id
                ON import_history(account_id)
            """)

            print("✓ import_history table created")
        else:
            print("✓ import_history table already exists")

        # Check if import_session_id column exists in transactions
        result = con.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.columns
            WHERE table_name = 'transactions' AND column_name = 'import_session_id'
        """).fetchone()

        if result[0] == 0:
            print("Adding import_session_id column to transactions...")

            # Add column
            con.execute("""
                ALTER TABLE transactions
                ADD COLUMN import_session_id INTEGER
            """)

            # Create index
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_import_session
                ON transactions(import_session_id)
            """)

            print("✓ import_session_id column added to transactions")
        else:
            print("✓ import_session_id column already exists")

        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        con.close()


if __name__ == "__main__":
    # Default database path
    db_path = Path(__file__).parent.parent / "sankash.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Please provide the correct path to your database.")
    else:
        migrate_database(str(db_path))
