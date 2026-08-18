from __future__ import annotations

from pathlib import Path
from typing import Any

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collection


SOURCE = "wolfcoffee.co.nz"


def _is_not_gift_card(product: dict[str, Any]) -> bool:
    product_type = str(product.get("product_type") or product.get("type") or "").casefold()
    title = str(product.get("title", "")).casefold()
    handle = str(product.get("handle", "")).casefold()
    tags = product.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",")]
    return not (
        product_type == "gift card"
        or "gift card" in title
        or "gift-card" in handle
        or any(str(tag).strip().casefold() == "gift card" for tag in tags)
    )


def scrape_wolf(database_path: Path | None = None) -> list[CoffeeListing]:
    return scrape_shopify_collection(
        SOURCE,
        "coffee-beans",
        database_path,
        product_filter=_is_not_gift_card,
    )
