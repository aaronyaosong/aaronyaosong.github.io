from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nz_coffee_tracker.models import CoffeeListing
from nz_coffee_tracker.scrapers.shopify_roaster import scrape_shopify_collection


SOURCE = "vanguardcoffee.co.nz"


def _is_roasted_coffee(product: dict[str, Any]) -> bool:
    text = " ".join(str(product.get(field, "")) for field in ("title", "handle")).casefold()
    return not re.search(r"\b(?:mineral|capsules?|drip\s+bags?)\b", text)


def scrape_vanguard(database_path: Path | None = None) -> list[CoffeeListing]:
    return scrape_shopify_collection(
        SOURCE,
        "coffee-beans",
        database_path,
        product_filter=_is_roasted_coffee,
    )
