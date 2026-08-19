from __future__ import annotations

from pathlib import Path

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collections


SOURCE = "c4coffee.co"


def scrape_c4(database_path: Path | None = None) -> list[CoffeeListing]:
    return scrape_shopify_collections(
        SOURCE,
        ["filter-extraction", "coffee"],
        database_path,
    )
