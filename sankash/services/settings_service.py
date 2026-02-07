"""Settings service for key-value configuration stored in DuckDB."""

from sankash.core.database import execute_command, execute_query


def get_setting(db_path: str, key: str, default: str | None = None) -> str | None:
    """Get a single setting by key, returning default if not found."""
    df = execute_query(
        db_path,
        "SELECT value FROM settings WHERE key = $key",
        {"key": key},
    )
    if df.is_empty():
        return default
    return df["value"][0]


def set_setting(db_path: str, key: str, value: str) -> None:
    """Upsert a setting (insert or update)."""
    execute_command(
        db_path,
        """INSERT INTO settings (key, value) VALUES ($key, $value)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
        {"key": key, "value": value},
    )


def get_all_settings(db_path: str) -> dict[str, str]:
    """Get all settings as a dict."""
    df = execute_query(db_path, "SELECT key, value FROM settings")
    if df.is_empty():
        return {}
    return dict(zip(df["key"].to_list(), df["value"].to_list()))
