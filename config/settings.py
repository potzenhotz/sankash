"""Application settings management using functional approach."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings."""

    db_path: str = Field(default="sankash.duckdb")
    default_currency: str = Field(default="EUR")
    date_format: str = Field(default="%Y-%m-%d")
    import_chunk_size: int = Field(default=1000)


def load_settings(config_path: Path | str = "config/settings.yaml") -> Settings:
    """
    Load settings from YAML file (pure function).

    Returns Settings instance with defaults if file doesn't exist.
    """
    path = Path(config_path)

    if not path.exists():
        return Settings()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    return Settings(**data)
