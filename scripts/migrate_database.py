"""Database migration script to add match_type column to rules table."""

import sys
from pathlib import Path

# Add parent directory to path to import sankash modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sankash.core.database import execute_command, get_connection


def run_migration(db_path: str):
    """Run the migration to add match_type column."""
    print(f"Running migration on database: {db_path}")

    # DuckDB doesn't support adding columns with NOT NULL constraint directly
    # So we add the column, set default values, then we can use it
    migration_sql = """
    ALTER TABLE rules ADD COLUMN IF NOT EXISTS match_type VARCHAR DEFAULT 'all';
    """

    update_sql = """
    UPDATE rules SET match_type = 'all' WHERE match_type IS NULL;
    """

    try:
        # Check if column already exists
        with get_connection(db_path) as con:
            result = con.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'rules' AND column_name = 'match_type'
            """).fetchall()

            if result:
                print("✓ Column 'match_type' already exists. Skipping migration.")
                return

        # Add the column
        execute_command(db_path, migration_sql)
        # Update existing rows to ensure they have the default value
        execute_command(db_path, update_sql)
        print("✓ Migration completed successfully!")
        print("  - Added 'match_type' column to 'rules' table")
        print("  - Set default value 'all' (AND logic) for all existing rules")

    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default database path
        db_path = "sankash.db"

    run_migration(db_path)
