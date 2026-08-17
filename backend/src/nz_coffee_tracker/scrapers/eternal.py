from __future__ import annotations

from pathlib import Path

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collection


SOURCE = "eternalcoffee.co.nz"


def scrape_eternal(database_path: Path | None = None) -> list[CoffeeListing]:
    # Eternal has no populated coffee collection, so its all-products feed is filtered by roast category.
    return scrape_shopify_collection(SOURCE, "all", database_path)
