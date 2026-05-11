"""Enrichment service for updating transaction payee/notes from Amazon and PayPal exports."""

import re
from datetime import timedelta
from pathlib import Path

import polars as pl

from sankash.core.models import ImportHistory
from sankash.core.storage import read_parquet, write_parquet
from sankash.services.import_history_service import (
    calculate_file_hash,
    create_import_history,
)
from sankash.services.transaction_service import split_transaction


def _record_enrichment_history(
    data_dir: str,
    file_path: str | Path,
    source: str,
    stats: dict[str, int],
) -> int | None:
    """Log an enrichment upload to import_history so it shows alongside CSV imports.

    Uses account_id=0 as a sentinel for cross-account enrichment files (no real
    account is tied to an Amazon/PayPal export). bank_format identifies the
    source: "amazon_enrichment" or "paypal_enrichment".
    """
    try:
        path = Path(file_path)
        record = ImportHistory(
            filename=path.name,
            account_id=0,
            bank_format=f"{source}_enrichment",
            total_count=int(stats.get(f"total_{source}", 0)),
            imported_count=int(stats.get("matched", 0)) + int(stats.get("children", 0)),
            duplicate_count=int(stats.get("skipped", 0)),
            categorized_count=0,
            file_hash=calculate_file_hash(path),
        )
        return create_import_history(data_dir, record)
    except Exception:
        # Don't fail the enrichment run because of a history-logging issue.
        return None


# --- Amazon enrichment ---

# Regex for Amazon order ID in transaction notes (e.g. 303-6572107-7229137 or D01-6611823-9851859)
AMAZON_ORDER_ID_RE = re.compile(r"[A-Z0-9]{3}-\d{7}-\d{7}")


def parse_amazon_csv_items(file_path: str | Path) -> pl.DataFrame:
    """Parse Amazon order history CSV into per-item rows.

    Returns DataFrame with columns: order_id, product_name, unit_price.
    """
    df = pl.read_csv(
        file_path,
        truncate_ragged_lines=True,
        null_values=["Not Available", "N/A", ""],
        infer_schema_length=0,
    )
    return df.select([
        pl.col("Order ID").alias("order_id"),
        pl.col("Product Name").alias("product_name"),
        pl.col("Unit Price").str.replace_all(",", "").cast(pl.Float64, strict=False).alias("unit_price"),
    ])


def parse_amazon_csv(file_path: str | Path) -> pl.DataFrame:
    """Parse Amazon order history CSV export, grouped by order_id.

    Returns DataFrame with columns: order_id, product_names, total_price, item_count.
    """
    items = parse_amazon_csv_items(file_path)
    return items.group_by("order_id").agg([
        pl.col("product_name").str.concat(", ").alias("product_names"),
        pl.col("unit_price").sum().alias("total_price"),
        pl.col("product_name").count().alias("item_count"),
    ])


def extract_order_id(notes: str) -> str | None:
    """Extract Amazon order ID from transaction notes."""
    if not notes:
        return None
    match = AMAZON_ORDER_ID_RE.search(notes)
    return match.group(0) if match else None


def enrich_with_amazon(
    data_dir: str,
    file_path: str | Path,
) -> dict[str, int]:
    """Enrich transactions with Amazon order data.

    Matches by order ID found in transaction notes.

    Single-item orders: prepend the product name to the transaction's notes.
    Multi-item orders: split the transaction into per-item child rows. Each child's
    notes is the product name; amounts are pro-rated by unit_price / total_price
    so the children sum to the original (handles shipping/discount drift).

    Returns dict with stats: matched, skipped, split (number of orders split),
    children (total child rows created), total_amazon.
    """
    items_df = parse_amazon_csv_items(file_path)
    amazon_df = items_df.group_by("order_id").agg([
        pl.col("product_name").str.concat(", ").alias("product_names"),
        pl.col("unit_price").sum().alias("total_price"),
        pl.col("product_name").count().alias("item_count"),
    ])

    txn_df = read_parquet(data_dir, "transactions")
    if txn_df.is_empty():
        return {"matched": 0, "skipped": 0, "split": 0, "children": 0, "total_amazon": len(amazon_df)}

    # Backfill parent_id col
    if "parent_id" not in txn_df.columns:
        txn_df = txn_df.with_columns(pl.lit(None).cast(pl.Int64).alias("parent_id"))

    # Only operate on parent/standalone rows (no parent_id) — never re-split a child.
    base_df = txn_df.filter(pl.col("parent_id").is_null()).with_columns(
        pl.col("notes")
        .map_elements(extract_order_id, return_dtype=pl.Utf8)
        .alias("_order_id")
    )

    matched = base_df.filter(
        pl.col("_order_id").is_not_null()
        & pl.col("_order_id").is_in(amazon_df["order_id"])
    ).join(amazon_df, left_on="_order_id", right_on="order_id", how="left")

    # Lookup table for per-item splits (order_id -> list of (product_name, unit_price))
    items_by_order: dict[str, list[tuple[str, float]]] = {}
    for row in items_df.iter_rows(named=True):
        items_by_order.setdefault(row["order_id"], []).append(
            (row["product_name"] or "", float(row["unit_price"] or 0.0))
        )

    # Already-split parents: txns that already have children in the parquet
    already_split_ids: set[int] = set(
        int(p) for p in (
            txn_df.filter(pl.col("parent_id").is_not_null())
            .select("parent_id").unique().to_series().to_list()
        ) if p is not None
    )

    note_updates: dict[int, str] = {}
    splits_to_apply: list[tuple[int, list[dict]]] = []
    skipped = 0

    for row in matched.iter_rows(named=True):
        tx_id = row["id"]
        if tx_id in already_split_ids:
            skipped += 1
            continue

        order_id = row["_order_id"]
        item_count = row["item_count"] or 0
        product_names = row["product_names"] or ""
        old_notes = row["notes"] or ""

        if item_count > 1:
            # Multi-item order → split children
            items = items_by_order.get(order_id, [])
            total_unit = sum(p for _, p in items) or 1.0
            parent_amount = float(row["amount"])
            child_splits = []
            for product_name, unit_price in items:
                share = (unit_price / total_unit) if total_unit else (1.0 / max(len(items), 1))
                child_splits.append({
                    "notes": product_name,
                    "amount": round(parent_amount * share, 2),
                })
            # Adjust last child to absorb rounding drift so children sum exactly to parent
            if child_splits:
                diff = round(parent_amount - sum(c["amount"] for c in child_splits), 2)
                child_splits[-1]["amount"] = round(child_splits[-1]["amount"] + diff, 2)
            splits_to_apply.append((tx_id, child_splits))
        else:
            # Single-item order → prepend product to notes
            name = product_names
            if len(name) > 120:
                name = name[:117] + "..."
            if old_notes.startswith(name):
                skipped += 1
                continue
            note_updates[tx_id] = f"{name} | {old_notes}" if old_notes else name

    # Apply notes updates to single-item orders
    if note_updates:
        update_ids = list(note_updates.keys())
        notes_map = note_updates
        txn_df = txn_df.with_columns([
            pl.when(pl.col("id").is_in(update_ids))
            .then(pl.col("id").map_elements(lambda x: notes_map.get(x, ""), return_dtype=pl.Utf8))
            .otherwise(pl.col("notes"))
            .alias("notes"),
        ])
        write_parquet(data_dir, "transactions", txn_df)

    # Apply splits for multi-item orders
    total_children = 0
    for parent_id, child_splits in splits_to_apply:
        new_ids = split_transaction(data_dir, parent_id, child_splits)
        total_children += len(new_ids)

    stats = {
        "matched": len(note_updates) + len(splits_to_apply),
        "skipped": skipped,
        "split": len(splits_to_apply),
        "children": total_children,
        "total_amazon": len(amazon_df),
    }
    _record_enrichment_history(data_dir, file_path, "amazon", stats)
    return stats


# --- PayPal enrichment ---


def parse_paypal_csv(file_path: str | Path) -> pl.DataFrame:
    """Parse PayPal activity CSV export (German format).

    Builds a mapping from Bankgutschrift amounts+dates to merchant names
    by following Zugehöriger Transaktionscode links.
    """
    df = pl.read_csv(
        file_path,
        separator=",",
        truncate_ragged_lines=True,
        encoding="utf-8",
    )

    # Normalize column names (PayPal uses quoted headers)
    df = df.rename({c: c.strip().strip('"') for c in df.columns})

    # Parse date and amount
    df = df.with_columns([
        pl.col("Datum").str.strptime(pl.Date, "%d.%m.%Y").alias("date"),
        pl.col("Brutto")
        .str.replace_all(r"\.", "")
        .str.replace(",", ".")
        .cast(pl.Float64)
        .alias("amount"),
        pl.col("Transaktionscode").alias("tx_code"),
        pl.col("Zugehöriger Transaktionscode").alias("related_code"),
        pl.col("Name").alias("merchant_name"),
        pl.col("Beschreibung").alias("description"),
    ])

    # Separate purchases and bank pulls
    purchases = df.filter(
        (pl.col("amount") < 0)
        & ~pl.col("description").str.contains("Bankgutschrift")
    ).select(["tx_code", "merchant_name", "amount", "date"])

    bank_pulls = df.filter(
        pl.col("description").str.contains("Bankgutschrift")
    ).select([
        pl.col("related_code"),
        pl.col("amount").alias("pull_amount"),
        pl.col("date").alias("pull_date"),
    ])

    # Join: bank pull -> purchase it funded
    linked = bank_pulls.join(
        purchases,
        left_on="related_code",
        right_on="tx_code",
        how="left",
    )

    # Group by bank pull (in case multiple purchases per pull)
    # Use pull_amount and pull_date for matching to bank transactions
    result = linked.group_by(["pull_amount", "pull_date"]).agg([
        pl.col("merchant_name").str.concat(", ").alias("merchant_names"),
        pl.col("merchant_name").count().alias("item_count"),
    ])

    return result


def enrich_with_paypal(
    data_dir: str,
    file_path: str | Path,
    date_tolerance_days: int = 3,
) -> dict[str, int]:
    """Enrich transactions with PayPal merchant data.

    Matches bank PayPal transactions by amount and approximate date
    to Bankgutschrift entries, then follows links to actual purchases.

    Returns dict with enrichment stats.
    """
    paypal_df = parse_paypal_csv(file_path)
    txn_df = read_parquet(data_dir, "transactions")

    if txn_df.is_empty() or paypal_df.is_empty():
        return {"matched": 0, "skipped": 0, "total_paypal": len(paypal_df)}

    # Filter to PayPal transactions only
    paypal_txns = txn_df.filter(
        pl.col("payee").str.to_lowercase().str.contains("paypal")
    )

    # Skip already-enriched (payee no longer starts with PayPal)
    needs_enrichment = paypal_txns.filter(
        pl.col("payee").str.to_lowercase().str.contains("paypal")
    )

    updates: dict[int, str] = {}
    skipped = 0

    for txn_row in needs_enrichment.iter_rows(named=True):
        txn_amount = txn_row["amount"]
        txn_date = txn_row["date"]
        target_amount = abs(txn_amount)

        for pp_row in paypal_df.iter_rows(named=True):
            pp_amount = pp_row["pull_amount"]
            pp_date = pp_row["pull_date"]

            if (
                abs(pp_amount - target_amount) < 0.01
                and abs((txn_date - pp_date).days) <= date_tolerance_days
            ):
                merchant = pp_row["merchant_names"]
                if merchant and merchant.strip():
                    if len(merchant) > 120:
                        merchant = merchant[:117] + "..."
                    old_notes = txn_row["notes"] or ""
                    if old_notes.startswith(merchant):
                        skipped += 1
                    else:
                        new_notes = f"{merchant} | {old_notes}" if old_notes else merchant
                        updates[txn_row["id"]] = new_notes
                break

    if updates:
        update_ids = list(updates.keys())
        new_notes_map = updates
        txn_df = txn_df.with_columns([
            pl.when(pl.col("id").is_in(update_ids))
            .then(
                pl.col("id").map_elements(
                    lambda x: new_notes_map.get(x, ""), return_dtype=pl.Utf8
                )
            )
            .otherwise(pl.col("notes"))
            .alias("notes"),
        ])

        write_parquet(data_dir, "transactions", txn_df)

    stats = {
        "matched": len(updates),
        "skipped": skipped,
        "total_paypal": len(paypal_df),
    }
    _record_enrichment_history(data_dir, file_path, "paypal", stats)
    return stats


def preview_enrichment(
    data_dir: str,
    file_path: str | Path,
    source: str,
    limit: int = 20,
) -> list[dict]:
    """Preview what enrichment would do without applying changes.

    Returns list of dicts with: id, date, old_payee, new_payee, amount.
    """
    txn_df = read_parquet(data_dir, "transactions")

    if source == "amazon":
        return _preview_amazon(txn_df, file_path, limit)
    elif source == "paypal":
        return _preview_paypal(txn_df, file_path, limit)
    return []


def _preview_amazon(txn_df: pl.DataFrame, file_path: str | Path, limit: int) -> list[dict]:
    """Preview Amazon enrichment matches."""
    amazon_df = parse_amazon_csv(file_path)

    # Only consider parent/standalone rows (no parent_id) so we don't try to
    # re-enrich existing split children.
    if "parent_id" in txn_df.columns:
        txn_df = txn_df.filter(pl.col("parent_id").is_null())

    txn_df = txn_df.with_columns(
        pl.col("notes")
        .map_elements(extract_order_id, return_dtype=pl.Utf8)
        .alias("_order_id")
    )

    matched = txn_df.filter(
        pl.col("_order_id").is_not_null()
        & pl.col("_order_id").is_in(amazon_df["order_id"])
    )

    enriched = matched.join(
        amazon_df,
        left_on="_order_id",
        right_on="order_id",
        how="left",
    )

    results = []
    for row in enriched.head(limit).iter_rows(named=True):
        product_names = row["product_names"] or ""
        item_count = row["item_count"] or 0
        if len(product_names) > 120:
            product_names = product_names[:117] + "..."
        old_notes = row["notes"] or ""
        already_enriched = old_notes.startswith(product_names)
        if item_count > 1:
            new_notes = f"→ split into {item_count} items: {product_names}"
        else:
            new_notes = old_notes if already_enriched else (
                f"{product_names} | {old_notes}" if old_notes else product_names
            )
        results.append({
            "id": row["id"],
            "date": str(row["date"]),
            "old_payee": row["payee"],
            "new_payee": row["payee"],
            "old_notes": old_notes,
            "new_notes": new_notes,
            "amount": row["amount"],
            "already_enriched": already_enriched,
            "will_split": item_count > 1,
            "item_count": int(item_count) if item_count else 0,
        })

    return results


def _preview_paypal(txn_df: pl.DataFrame, file_path: str | Path, limit: int) -> list[dict]:
    """Preview PayPal enrichment matches."""
    paypal_df = parse_paypal_csv(file_path)

    paypal_txns = txn_df.filter(
        pl.col("payee").str.to_lowercase().str.contains("paypal")
    )

    results = []
    for txn_row in paypal_txns.head(limit).iter_rows(named=True):
        target_amount = abs(txn_row["amount"])
        txn_date = txn_row["date"]

        matched_merchant = None
        for pp_row in paypal_df.iter_rows(named=True):
            if (
                abs(pp_row["pull_amount"] - target_amount) < 0.01
                and abs((txn_date - pp_row["pull_date"]).days) <= 3
            ):
                matched_merchant = pp_row["merchant_names"]
                break

        if matched_merchant:
            if len(matched_merchant) > 120:
                matched_merchant = matched_merchant[:117] + "..."
            old_notes = txn_row["notes"] or ""
            already_enriched = old_notes.startswith(matched_merchant)
            new_notes = old_notes if already_enriched else (f"{matched_merchant} | {old_notes}" if old_notes else matched_merchant)
            results.append({
                "id": txn_row["id"],
                "date": str(txn_row["date"]),
                "old_payee": txn_row["payee"],
                "new_payee": txn_row["payee"],
                "old_notes": old_notes,
                "new_notes": new_notes,
                "amount": txn_row["amount"],
                "already_enriched": already_enriched,
            })

    return results


def migrate_enriched_payees(data_dir: str) -> dict[str, int]:
    """Migrate old-style enriched payees (Amazon:/PayPal: prefix) to notes.

    Old format: payee = "Amazon: Kindle Paperwhite", notes = "303-xxx"
    New format: payee = "AMAZON",                    notes = "Kindle Paperwhite | 303-xxx"
    """
    txn_df = read_parquet(data_dir, "transactions")

    if txn_df.is_empty():
        return {"amazon": 0, "paypal": 0}

    amazon_rows = txn_df.filter(pl.col("payee").str.starts_with("Amazon: "))
    paypal_rows = txn_df.filter(pl.col("payee").str.starts_with("PayPal: "))

    if amazon_rows.is_empty() and paypal_rows.is_empty():
        return {"amazon": 0, "paypal": 0}

    def _new_notes(old_payee: str, prefix: str, old_notes: str) -> str:
        product = old_payee[len(prefix):]
        return f"{product} | {old_notes}" if old_notes else product

    all_updates: dict[int, tuple[str, str]] = {}
    for row in amazon_rows.iter_rows(named=True):
        all_updates[row["id"]] = ("AMAZON", _new_notes(row["payee"], "Amazon: ", row["notes"] or ""))
    for row in paypal_rows.iter_rows(named=True):
        all_updates[row["id"]] = ("PAYPAL", _new_notes(row["payee"], "PayPal: ", row["notes"] or ""))

    if all_updates:
        update_ids = list(all_updates.keys())
        payee_map = {tid: v[0] for tid, v in all_updates.items()}
        notes_map = {tid: v[1] for tid, v in all_updates.items()}

        txn_df = txn_df.with_columns([
            pl.when(pl.col("id").is_in(update_ids))
            .then(pl.col("id").map_elements(lambda x: payee_map.get(x, ""), return_dtype=pl.Utf8))
            .otherwise(pl.col("payee"))
            .alias("payee"),
            pl.when(pl.col("id").is_in(update_ids))
            .then(pl.col("id").map_elements(lambda x: notes_map.get(x, ""), return_dtype=pl.Utf8))
            .otherwise(pl.col("notes"))
            .alias("notes"),
        ])

        write_parquet(data_dir, "transactions", txn_df)

    return {"amazon": len(amazon_rows), "paypal": len(paypal_rows)}
