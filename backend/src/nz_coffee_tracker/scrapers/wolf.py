from __future__ import annotations

from pathlib import Path
from typing import Any

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collections


SOURCE = "wolfcoffee.co.nz"


def _is_not_gift_card(product: dict[str, Any]) -> bool:
    product_type = str(product.get("product_type") or product.get("type") or "").casefold()
    title = str(product.get("title", "")).casefold()
    handle = str(product.get("handle", "")).casefold()
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",")]
    elif not isinstance(tags, list):
        tags = [tags]
    return not (
        product_type in ("gift card", "merch", "filters", "brew gear")
        or "gift card" in title
        or "gift-card" in handle
        or any(str(tag).strip().casefold() in ("gift card", "filters", "brew gear") for tag in tags)
    )


def scrape_wolf(database_path: Path | None = None) -> list[CoffeeListing]:
    return scrape_shopify_collections(
        SOURCE,
        ["single-origins", "house-blends"],
        database_path,
        product_filter=_is_not_gift_card,
    )
