from __future__ import annotations

from pathlib import Path
from typing import Any

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collections


SOURCE = "greyroastingco.com"


def _is_coffee_product(product: dict[str, Any]) -> bool:
    product_type = str(product.get("product_type") or product.get("type") or "").strip().casefold()
    if product_type == "coffee":
        return True
    tags = product.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",")]
    return any(str(tag).strip().casefold() == "coffee" for tag in tags)


def scrape_grey_roasting_co(database_path: Path | None = None) -> list[CoffeeListing]:
    listings = scrape_shopify_collections(
        SOURCE,
        ["single-origin-coffees", "espresso-blends-decaf"],
        database_path,
        product_filter=_is_coffee_product,
    )
    return [
        listing
        for listing in listings
        if "subscription" not in f"{listing.title} {listing.handle}".lower()
    ]