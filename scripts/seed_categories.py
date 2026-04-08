"""Seed default categories script."""

from sankash.services.category_service import seed_default_categories
from config.settings import load_settings


def main() -> None:
    """Seed with default categories."""
    settings = load_settings()

    print(f"Seeding default categories to: {settings.data_dir}")
    seed_default_categories(settings.data_dir)
    print("Default categories created successfully!")


if __name__ == "__main__":
    main()
