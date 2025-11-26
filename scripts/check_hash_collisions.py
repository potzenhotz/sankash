"""Check for imported_id hash collisions in database."""

import sys
from sankash.core.database import execute_query


def check_collisions(db_path: str):
    """Check for imported_id collisions in the database."""

    # Get all transactions with their imported_ids
    query = """
    SELECT
        COUNT(*) as total,
        COUNT(DISTINCT imported_id) as unique_ids
    FROM transactions
    """

    result = execute_query(db_path, query)
    total = result['total'][0]
    unique_ids = result['unique_ids'][0]

    print(f"Total transactions in database: {total}")
    print(f"Unique imported_ids: {unique_ids}")
    print(f"Collisions (same imported_id): {total - unique_ids}\n")

    # Find actual collisions
    if total != unique_ids:
        collision_query = """
        SELECT imported_id, COUNT(*) as count
        FROM transactions
        GROUP BY imported_id
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        """
        collisions = execute_query(db_path, collision_query)
        print(f"Imported IDs with collisions:")
        print(collisions)

    # Check for null imported_ids
    null_query = """
    SELECT COUNT(*) as null_count
    FROM transactions
    WHERE imported_id IS NULL
    """
    nulls = execute_query(db_path, null_query)
    print(f"\nTransactions with NULL imported_id: {nulls['null_count'][0]}")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "sankash.duckdb"
    check_collisions(db_path)
