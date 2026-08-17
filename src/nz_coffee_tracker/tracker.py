from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from nz_coffee_tracker.categorization import category_values
from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.atomic import scrape_atomic
from nz_coffee_tracker.scrapers.rocket import scrape_rocket


DEFAULT_ALLOWED_CATEGORIES = {"filter roast", "espresso roast"}


def _matches_categories(item: CoffeeListing, allowed_categories: set[str] | None) -> bool:
    if allowed_categories is None:
        return True
    return bool(category_values(item.category) & allowed_categories)


def collect_listings(
    include_unavailable: bool = False,
    allowed_categories: set[str] | None = DEFAULT_ALLOWED_CATEGORIES,
) -> list[CoffeeListing]:
    listings = [*scrape_rocket(), *scrape_atomic()]

    filtered = [item for item in listings if _matches_categories(item, allowed_categories)]
    if include_unavailable:
        return filtered
    return [item for item in filtered if item.available]


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(listings: Iterable[CoffeeListing], path: Path) -> None:
    rows = [item.to_dict() for item in listings]
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(rows),
        "items": rows,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(listings: Iterable[CoffeeListing], path: Path) -> None:
    rows = [item.to_dict() for item in listings]
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    headers = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def persist_snapshots(listings: list[CoffeeListing], out_dir: Path, output_format: str = "both") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp_slug()
    written: dict[str, Path] = {}

    if output_format in {"json", "both"}:
        latest_json = out_dir / "latest.json"
        snap_json = out_dir / f"{stamp}.json"
        write_json(listings, latest_json)
        write_json(listings, snap_json)
        written["latest_json"] = latest_json
        written["snapshot_json"] = snap_json

    if output_format in {"csv", "both"}:
        latest_csv = out_dir / "latest.csv"
        snap_csv = out_dir / f"{stamp}.csv"
        write_csv(listings, latest_csv)
        write_csv(listings, snap_csv)
        written["latest_csv"] = latest_csv
        written["snapshot_csv"] = snap_csv

    return written
