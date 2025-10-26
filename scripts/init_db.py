"""Initialize database script."""

from pathlib import Path
from sankash.core.database import init_database
from config.settings import load_settings


def main() -> None:
    """Initialize the database with schema."""
    settings = load_settings()

    print(f"Initializing database at: {settings.db_path}")
    init_database(settings.db_path)
    print("Database initialized successfully!")


if __name__ == "__main__":
    main()
