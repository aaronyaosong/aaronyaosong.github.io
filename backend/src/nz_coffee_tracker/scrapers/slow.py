from __future__ import annotations

from pathlib import Path

from nz_coffee_tracker.categorization import ESPRESSO_ROAST
from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collections


SOURCE = "slowcoffee.co.nz"


def scrape_slow(database_path: Path | None = None) -> list[CoffeeListing]:
    listings = scrape_shopify_collections(
        SOURCE,
        ["filter-coffee", "espresso-coffee"],
        database_path,
    )
    for listing in listings:
        if "raspberry kiss" in listing.title.lower() or "raspberry-kiss" in listing.handle.lower():
            listing.category = ESPRESSO_ROAST
    return listings
