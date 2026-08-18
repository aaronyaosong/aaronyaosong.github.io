from __future__ import annotations

from pathlib import Path

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collection


SOURCE = "vanguardcoffee.co.nz"


def scrape_vanguard(database_path: Path | None = None) -> list[CoffeeListing]:
    return scrape_shopify_collection(SOURCE, "coffee-beans", database_path)
