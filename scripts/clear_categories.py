"""Clear all categories from the database."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from sankash.core.database import execute_command


def main() -> None:
    """Clear all categories."""
    print("🗑️  Clearing all categories...")
    
    settings = load_settings()
    db_path = settings.db_path
    
    # First uncategorize all transactions
    execute_command(
        db_path,
        "UPDATE transactions SET category = NULL, is_categorized = FALSE WHERE category IS NOT NULL"
    )
    
    # Then delete all categories
    execute_command(db_path, "DELETE FROM categories")
    
    # Reset the sequence
    execute_command(db_path, "DROP SEQUENCE IF EXISTS seq_categories_id")
    execute_command(db_path, "CREATE SEQUENCE seq_categories_id START 1")
    
    print("✅ All categories cleared")
    print()


if __name__ == "__main__":
    main()
