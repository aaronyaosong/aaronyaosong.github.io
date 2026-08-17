from __future__ import annotations

import re
from typing import Any


FILTER_ROAST = "filter roast"
ESPRESSO_ROAST = "espresso roast"
OTHER_CATEGORY = "other"


def _normalize_text(raw: str) -> str:
    compact = re.sub(r"\s+", " ", raw).strip().lower()
    return compact


def _collect_product_text(product: dict[str, Any]) -> str:
    # Build one searchable text blob from common Shopify product fields.
    chunks: list[str] = []
    for key in ("title", "handle", "body_html", "product_type", "tags"):
        value = product.get(key)
        if value:
            chunks.append(str(value))

    for option in product.get("options", []):
        if option.get("name"):
            chunks.append(str(option["name"]))
        for value in option.get("values", []):
            chunks.append(str(value))

    for variant in product.get("variants", []):
        if variant.get("title"):
            chunks.append(str(variant["title"]))

    return _normalize_text(" ".join(chunks))


def infer_roast_category(product: dict[str, Any]) -> str:
    # Categories are keyword-based so the same rule works across multiple roasters.
    text = _collect_product_text(product)
    has_filter = bool(re.search(r"\bfilter\b", text))
    has_espresso = bool(re.search(r"\bespresso\b", text))

    if has_filter and has_espresso:
        return f"{FILTER_ROAST},{ESPRESSO_ROAST}"
    if has_filter:
        return FILTER_ROAST
    if has_espresso:
        return ESPRESSO_ROAST
    return OTHER_CATEGORY


def category_values(category: str) -> set[str]:
    # Split compound category values like "filter roast,espresso roast".
    return {part.strip() for part in category.split(",") if part.strip()}
