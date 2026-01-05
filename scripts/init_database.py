"""Initialize database with schema."""

import duckdb
from pathlib import Path


def init_database(db_path: str, schema_path: str) -> None:
    """Initialize database with schema."""
    print(f"Initializing database: {db_path}")

    # Read schema
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Connect and create tables
    con = duckdb.connect(db_path)

    try:
        # Execute schema
        con.execute(schema_sql)
        print("✅ Database initialized successfully!")

        # Show created tables
        tables = con.execute("SHOW TABLES").fetchall()
        print(f"\nCreated tables: {[t[0] for t in tables]}")

    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        raise
    finally:
        con.close()


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "sankash.db"
    schema_path = Path(__file__).parent.parent / "sankash" / "core" / "schema.sql"

    init_database(str(db_path), str(schema_path))
