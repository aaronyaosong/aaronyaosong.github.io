from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
import json
from pathlib import Path

from nz_coffee_tracker.models import CoffeeListing


SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY,
    scraped_at TEXT NOT NULL,
    listing_count INTEGER NOT NULL,
    include_unavailable INTEGER NOT NULL,
    category_filter TEXT
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs(id),
    source TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    handle TEXT NOT NULL,
    product_url TEXT NOT NULL,
    available INTEGER NOT NULL,
    price_min_nzd REAL NOT NULL,
    price_max_nzd REAL NOT NULL,
    updated_at TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    varietal TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS size_prices (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    size_grams REAL NOT NULL,
    price_nzd REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_product
    ON listings(source, product_id, scraped_at);
CREATE INDEX IF NOT EXISTS idx_listings_category
    ON listings(category, scraped_at);
CREATE INDEX IF NOT EXISTS idx_size_prices_listing
    ON size_prices(listing_id);
"""


def write_database(
    listings: Iterable[CoffeeListing],
    path: Path,
    *,
    include_unavailable: bool = False,
    category_filter: set[str] | None = None,
) -> Path:
    rows = list(listings)
    path.parent.mkdir(parents=True, exist_ok=True)
    scraped_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        run = connection.execute(
            """
            INSERT INTO scrape_runs (scraped_at, listing_count, include_unavailable, category_filter)
            VALUES (?, ?, ?, ?)
            """,
            (
                scraped_at,
                len(rows),
                int(include_unavailable),
                ",".join(sorted(category_filter)) if category_filter else None,
            ),
        )
        run_id = run.lastrowid

        for item in rows:
            listing = connection.execute(
                """
                INSERT INTO listings (
                    scrape_run_id, source, product_id, title, category, handle, product_url,
                    available, price_min_nzd, price_max_nzd, updated_at, scraped_at, varietal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item.source,
                    item.product_id,
                    item.title,
                    item.category,
                    item.handle,
                    item.product_url,
                    int(item.available),
                    item.price_min_nzd,
                    item.price_max_nzd,
                    item.updated_at,
                    item.scraped_at,
                    item.varietal,
                ),
            )
            listing_id = listing.lastrowid
            connection.executemany(
                "INSERT INTO size_prices (listing_id, size_grams, price_nzd) VALUES (?, ?, ?)",
                [(listing_id, row["size_grams"], row["price_nzd"]) for row in item.size_prices],
            )

    return path


def has_current_data(
    path: Path,
    out_dir: Path,
    output_format: str,
    *,
    include_unavailable: bool = False,
    category_filter: set[str] | None = None,
    today: str | None = None,
) -> bool:
    if not path.exists():
        return False

    required_outputs = []
    if output_format in {"json", "both"}:
        required_outputs.append(out_dir / "latest.json")
    if output_format in {"csv", "both"}:
        required_outputs.append(out_dir / "latest.csv")
    if any(not output.exists() or output.stat().st_size == 0 for output in required_outputs):
        return False

    if today is None:
        today = datetime.now(timezone.utc).date().isoformat()
    expected_filter = ",".join(sorted(category_filter)) if category_filter else None

    try:
        with sqlite3.connect(path) as connection:
            row = connection.execute(
                """
                SELECT listing_count
                FROM scrape_runs
                WHERE date(scraped_at) = ?
                  AND include_unavailable = ?
                  AND (category_filter = ? OR (category_filter IS NULL AND ? IS NULL))
                ORDER BY id DESC
                LIMIT 1
                """,
                (today, int(include_unavailable), expected_filter, expected_filter),
            ).fetchone()
    except sqlite3.DatabaseError:
        return False

    if not row or row[0] <= 0:
        return False

    latest_json = out_dir / "latest.json"
    if output_format not in {"json", "both"}:
        return True
    try:
        payload = json.loads(latest_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(payload.get("items"))


def latest_listing(path: Path, source: str, product_id: int) -> dict | None:
    if not path.exists():
        return None
    try:
        with sqlite3.connect(path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT l.id, l.available
                FROM listings AS l
                WHERE l.source = ? AND l.product_id = ?
                ORDER BY l.id DESC
                LIMIT 1
                """,
                (source, product_id),
            ).fetchone()
            if row is None:
                return None
            size_prices = connection.execute(
                "SELECT size_grams, price_nzd FROM size_prices WHERE listing_id = ? ORDER BY size_grams",
                (row["id"],),
            ).fetchall()
            return {
                "available": bool(row["available"]),
                "size_prices": [dict(size_price) for size_price in size_prices],
            }
    except sqlite3.DatabaseError:
        return None
