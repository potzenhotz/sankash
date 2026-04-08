"""Quick setup script to initialize Sankash."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from sankash.core.storage import init_data_dir


def main() -> None:
    """Run complete setup."""
    print("Setting up Sankash...")
    print()

    # Load settings
    settings = load_settings()
    data_dir = settings.data_dir

    # Initialize data directory
    print(f"Initializing data directory at: {data_dir}")
    init_data_dir(data_dir)
    print("Data directory initialized")
    print()

    print("Setup complete!")
    print()
    print("Next steps:")
    print("  1. Run: reflex run")
    print("  2. Open: http://localhost:3000")
    print("  3. Create an account in the Accounts page")
    print("  4. Import transactions via the Import page")
    print()


if __name__ == "__main__":
    main()
