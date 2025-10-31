"""Quick setup script to initialize Sankash."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from sankash.core.database import init_database


def main() -> None:
    """Run complete setup."""
    print("🚀 Setting up Sankash...")
    print()

    # Load settings
    settings = load_settings()
    db_path = settings.db_path

    # Initialize database
    print(f"📊 Initializing database at: {db_path}")
    init_database(db_path)
    print("✅ Database initialized")
    print()

    # Seed categories (commented out - users can create their own)
    # print("🏷️  Seeding default categories...")
    # seed_default_categories(db_path)
    # print("✅ Default categories created")
    # print()

    print("✨ Setup complete!")
    print()
    print("Next steps:")
    print("  1. Run: reflex run")
    print("  2. Open: http://localhost:3000")
    print("  3. Create an account in the Accounts page")
    print("  4. Import transactions via the Import page")
    print()


if __name__ == "__main__":
    main()
