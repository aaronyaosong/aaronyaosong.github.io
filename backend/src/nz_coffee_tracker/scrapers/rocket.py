from __future__ import annotations

from pathlib import Path

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collections


SOURCE = "rocketcoffee.co.nz"


def scrape_rocket(database_path: Path | None = None) -> list[CoffeeListing]:
    return scrape_shopify_collections(
        SOURCE,
        ["single-origin", "espresso-blends", "coffee"],
        database_path,
    )
