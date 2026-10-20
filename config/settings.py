"""Application settings management using functional approach."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    """Application settings."""

    data_dir: str = Field(default="data")
    default_currency: str = Field(default="EUR")
    date_format: str = Field(default="%Y-%m-%d")
    import_chunk_size: int = Field(default=1000)


def load_settings(config_path: Path | str = PROJECT_ROOT / "config" / "settings.yaml") -> Settings:
    """
    Load settings from YAML file (pure function).

    Returns Settings instance with defaults if file doesn't exist. A relative
    data_dir is resolved against the project root, so the result does not
    depend on the directory a server was started from.
    """
    path = Path(config_path)

    data: dict[str, Any] = {}
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}

    settings = Settings(**data)
    settings.data_dir = str(PROJECT_ROOT / settings.data_dir)  # no-op for absolute paths
    return settings
