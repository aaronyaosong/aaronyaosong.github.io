from __future__ import annotations

from pathlib import Path

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collection


SOURCE = "greyroastingco.com"


def scrape_grey_roasting_co(database_path: Path | None = None) -> list[CoffeeListing]:
    listings = scrape_shopify_collection(SOURCE, "all", database_path)
    return [
        listing
        for listing in listings
        if "subscription" not in f"{listing.title} {listing.handle}".lower()
    ]