"""File-based storage layer using Parquet, YAML, and JSON."""

import json
import os
from pathlib import Path
from typing import Any

import polars as pl
import yaml


# --- Parquet operations ---


def read_parquet(data_dir: str, name: str) -> pl.DataFrame:
    """Read a Parquet file, returning empty DataFrame if missing."""
    path = Path(data_dir) / f"{name}.parquet"
    if not path.exists():
        return pl.DataFrame()
    df = pl.read_parquet(path)
    # Ensure date column is Date type (may be string from older writes)
    if "date" in df.columns and df["date"].dtype == pl.Utf8:
        df = df.with_columns(pl.col("date").str.to_date())
    return df


def _ensure_dir(path: Path) -> None:
    """Ensure the parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def write_parquet(data_dir: str, name: str, df: pl.DataFrame) -> None:
    """Atomically write a DataFrame to Parquet."""
    path = Path(data_dir) / f"{name}.parquet"
    _ensure_dir(path)
    tmp = path.with_suffix(".parquet.tmp")
    df.write_parquet(tmp)
    os.replace(tmp, path)


def append_parquet(data_dir: str, name: str, new_df: pl.DataFrame) -> None:
    """Append rows to an existing Parquet file (or create it)."""
    existing = read_parquet(data_dir, name)
    if existing.is_empty():
        combined = new_df
    else:
        combined = pl.concat([existing, new_df], how="diagonal")
    write_parquet(data_dir, name, combined)


# --- YAML operations (config files) ---


def read_yaml(data_dir: str, name: str) -> list[dict[str, Any]]:
    """Read a YAML config file from data/config/, returning [] if missing."""
    path = Path(data_dir) / "config" / f"{name}.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def write_yaml(data_dir: str, name: str, records: list[dict[str, Any]]) -> None:
    """Atomically write records to a YAML config file."""
    path = Path(data_dir) / "config" / f"{name}.yaml"
    _ensure_dir(path)
    tmp = path.with_suffix(".yaml.tmp")
    with open(tmp, "w") as f:
        yaml.dump(records, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)


# --- JSON operations ---


def read_json(data_dir: str, name: str) -> list[dict[str, Any]] | dict[str, Any]:
    """Read a JSON file from data/, returning [] if missing."""
    path = Path(data_dir) / f"{name}.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def write_json(data_dir: str, name: str, data: list[dict[str, Any]] | dict[str, Any]) -> None:
    """Atomically write data to a JSON file."""
    path = Path(data_dir) / f"{name}.json"
    _ensure_dir(path)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    os.replace(tmp, path)


# --- Transaction overrides ---


def read_overrides(data_dir: str) -> dict[str, dict[str, Any]]:
    """Read transaction overrides. Keys are string transaction IDs."""
    data = read_json(data_dir, "transaction_overrides")
    if isinstance(data, dict):
        return data
    return {}


def write_overrides(data_dir: str, overrides: dict[str, dict[str, Any]]) -> None:
    """Atomically write transaction overrides."""
    write_json(data_dir, "transaction_overrides", overrides)


def merge_overrides(df: pl.DataFrame, overrides: dict[str, dict[str, Any]]) -> pl.DataFrame:
    """Merge transaction overrides onto a transactions DataFrame.

    Applies category, is_categorized, is_transfer, transfer_account_id
    from the overrides dict keyed by transaction ID.
    """
    if not overrides or df.is_empty():
        return df

    override_rows = []
    for tid, vals in overrides.items():
        row: dict[str, Any] = {"id": int(tid)}
        row.update(vals)
        override_rows.append(row)

    override_df = pl.DataFrame(override_rows)

    override_cols = [c for c in override_df.columns if c != "id"]
    if not override_cols:
        return df

    # Join overrides onto transactions, using override values where present
    result = df.join(override_df, on="id", how="left", suffix="_override")

    for col in override_cols:
        override_col = f"{col}_override"
        if override_col in result.columns:
            result = result.with_columns(
                pl.when(pl.col(override_col).is_not_null())
                .then(pl.col(override_col))
                .otherwise(pl.col(col))
                .alias(col)
            ).drop(override_col)

    return result


# --- ID generation ---


def next_id(data: list[dict[str, Any]] | pl.DataFrame) -> int:
    """Generate next sequential ID from existing records."""
    if isinstance(data, pl.DataFrame):
        if data.is_empty() or "id" not in data.columns:
            return 1
        return int(data["id"].max()) + 1  # type: ignore[arg-type]
    if not data:
        return 1
    return max(r.get("id", 0) for r in data) + 1


# --- Initialization ---


def init_data_dir(data_dir: str) -> None:
    """Create the data directory structure with empty files."""
    base = Path(data_dir)
    config = base / "config"
    config.mkdir(parents=True, exist_ok=True)

    # Create empty files if they don't exist
    defaults: dict[str, str] = {
        "transaction_overrides.json": "{}",
        "import_history.json": "[]",
        "config/accounts.yaml": "[]",
        "config/categories.yaml": "[]",
        "config/rules.yaml": "[]",
        "config/app_settings.yaml": "{}",
    }
    for filename, content in defaults.items():
        path = base / filename
        if not path.exists():
            with open(path, "w") as f:
                f.write(content)
