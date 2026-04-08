"""Settings service for key-value configuration stored in YAML."""

import os
from pathlib import Path

import yaml


def _settings_path(data_dir: str) -> Path:
    return Path(data_dir) / "config" / "app_settings.yaml"


def _read(data_dir: str) -> dict[str, str]:
    path = _settings_path(data_dir)
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _write(data_dir: str, settings: dict[str, str]) -> None:
    path = _settings_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    with open(tmp, "w") as f:
        yaml.dump(settings, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)


def get_setting(data_dir: str, key: str, default: str | None = None) -> str | None:
    """Get a single setting by key, returning default if not found."""
    return _read(data_dir).get(key, default)


def set_setting(data_dir: str, key: str, value: str) -> None:
    """Upsert a setting."""
    settings = _read(data_dir)
    settings[key] = value
    _write(data_dir, settings)


def get_all_settings(data_dir: str) -> dict[str, str]:
    """Get all settings as a dict."""
    return _read(data_dir)
