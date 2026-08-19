from __future__ import annotations

import re
from html import unescape
from typing import Any


FILTER_ROAST = "filter roast"
ESPRESSO_ROAST = "espresso roast"
OTHER_CATEGORY = "other"
KNOWN_VARIETALS = (
    "sudan rume",
    "ruiru 11",
    "maragogype",
    "pacamara",
    "castillo",
    "caturra",
    "catuai",
    "obata",
    "bourbon",
    "typica",
    "gesha",
    "geisha",
    "sidra",
    "java",
    "sl28",
    "sl34",
    "batian",
)


def _normalize_text(raw: str) -> str:
    compact = re.sub(r"\s+", " ", raw).strip().lower()
    return compact


def description_text(product: dict[str, Any]) -> str:
    raw = str(product.get("body_html") or product.get("description") or "")
    text = re.sub(r"<[^>]+>", " ", unescape(raw))
    return re.sub(r"\s+", " ", text).strip()


def extract_description_field(product: dict[str, Any], labels: tuple[str, ...]) -> str:
    text = description_text(product)
    label_pattern = "|".join(re.escape(label) for label in labels)
    next_label = r"origin(?: country)?|country|producer|farm|estate|process(?:ing)?|flavou?r notes|tasting notes|notes"
    match = re.search(
        rf"(?:{label_pattern})\s*[:\-]\s*(.*?)(?=\s+(?:{next_label})\s*[:\-]|$|[.;|\n])",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else "unknown"


def infer_origin_country(product: dict[str, Any]) -> str:
    return extract_description_field(product, ("origin", "origin country", "country"))


def infer_producer(product: dict[str, Any]) -> str:
    return extract_description_field(product, ("producer", "farm", "estate"))


def infer_process(product: dict[str, Any]) -> str:
    return extract_description_field(product, ("process", "processing"))


def infer_flavour_notes(product: dict[str, Any]) -> str:
    return extract_description_field(product, ("flavour notes", "flavor notes", "tasting notes", "notes"))


def infer_decaf(product: dict[str, Any]) -> bool:
    text = _collect_product_text(product)
    return bool(re.search(r"\bdecaf(?:f)?\b", text))


def _collect_product_text(product: dict[str, Any]) -> str:
    # Build one searchable text blob from common Shopify product fields without grind option noise.
    chunks: list[str] = []
    for key in ("title", "handle", "body_html", "product_type", "tags", "vendor"):
        value = product.get(key)
        if value:
            chunks.append(str(value))

    return _normalize_text(" ".join(chunks))


def _is_non_coffee(product: dict[str, Any]) -> bool:
    product_type = str(product.get("product_type") or product.get("type") or "").strip().lower()
    title = str(product.get("title", "")).strip().lower()
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tags = [str(t).strip().lower() for t in tags]

    non_coffee_types = {
        "gift card",
        "brew gear",
        "brewing equipment",
        "vessels",
        "scales",
        "merchandise",
        "merch",
        "spare parts",
        "clothing",
        "books",
        "filters",
        "apparel",
        "classes",
        "events",
        "machinery",
        "espresso equipment",
        "home espresso machines",
    }
    if product_type in non_coffee_types:
        return True

    if re.search(r"\b(?:gift\s*card|voucher|e-gift|t-shirt|tea\s*towel|tote\s*bag|paper\s*filters?|filter\s*papers?|dripper|grinder|scale|tamper|burr|server|pitcher|cup|mug)\b", title):
        return True

    return False


def infer_roast_category(
    product: dict[str, Any],
    collection_handle: str | None = None,
    source: str | None = None,
) -> str:
    if _is_non_coffee(product):
        return OTHER_CATEGORY

    title = str(product.get("title", "")).strip()
    handle = str(product.get("handle", "")).strip()
    p_type = str(product.get("product_type") or product.get("type") or "").strip()

    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = [str(tags)]
    tags_lower = [str(t).lower().strip() for t in tags]
    tags_str = " ".join(tags_lower)
    title_lower = title.lower()
    handle_lower = handle.lower()
    p_type_lower = p_type.lower()

    has_filter = False
    has_espresso = False

    # 1. Check collection context if provided
    if collection_handle:
        col = collection_handle.lower().strip()
        if col in (
            "filter",
            "filter-coffee",
            "single-origin-coffees",
            "specialty-coffee-beans-nz",
            "single-origin",
            "single-origins",
        ):
            has_filter = True
        elif col in (
            "espresso",
            "espresso-coffee",
            "espresso-blends",
            "espresso-offerings-1",
            "espresso-blends-decaf",
            "house-blends",
            "blends",
        ):
            has_espresso = True

    # 2. Check tags (do NOT inspect variant titles or options which contain grind choices)
    filter_tag_keywords = {
        "filter",
        "filter coffee",
        "filter roast",
        "filter brewing",
        "extraction-filter",
        "quiz-filter",
    }
    if any(t in filter_tag_keywords or "brew method:filter" in t or t.startswith("filter") for t in tags_lower):
        has_filter = True

    espresso_tag_keywords = {
        "espresso",
        "espresso coffee",
        "espresso roast",
        "extraction-espresso",
        "modern-espresso",
        "single espresso roast",
        "quiz-espresso",
    }
    if any(t in espresso_tag_keywords or "brew method:espresso" in t for t in tags_lower):
        has_espresso = True

    if any(t in ("extraction-omni", "omni roast", "omni") for t in tags_lower):
        has_filter = True
        has_espresso = True

    # 3. Check title and handle
    if re.search(r"\bfilter\s*roast\b|\(filter\)|\[[^\]]*filter[^\]]*\]|\bfilter\s*coffee\b", title_lower) or "filter-roast" in handle_lower:
        has_filter = True
    elif re.search(r"\bfilter\b", title_lower) and not re.search(r"\b(?:paper\s*filters?|filter\s*papers?|filter\s*basket|group\s*filter)\b", title_lower):
        has_filter = True

    if re.search(r"\bespresso\s*roast\b|\(espresso\)|\[[^\]]*espresso[^\]]*\]|\bespresso\s*blend\b", title_lower) or "espresso-roast" in handle_lower or "espresso-blend" in handle_lower:
        has_espresso = True
    elif re.search(r"\bespresso\b", title_lower) and not re.search(r"\b(?:espresso\s*machine|espresso\s*equipment|workshop)\b", title_lower):
        has_espresso = True

    if re.search(r"\bomni\s*roast\b|espresso\s*\/\s*filter", title_lower) or "omni-roast" in handle_lower:
        has_filter = True
        has_espresso = True

    # 4. Roaster-specific or fallback heuristics
    if not has_filter and not has_espresso:
        if (
            "blend" in title_lower
            or "blend" in tags_str
            or p_type_lower in ("coffee house", "house")
        ):
            has_espresso = True
        elif (
            "single origin" in tags_str
            or "single-origin" in tags_str
            or p_type_lower in ("single origin", "single origin specialty coffee", "coffee clarity", "coffee vibrant")
        ):
            has_filter = True

    if has_filter and has_espresso:
        return f"{FILTER_ROAST},{ESPRESSO_ROAST}"
    if has_filter:
        return FILTER_ROAST
    if has_espresso:
        return ESPRESSO_ROAST
    return OTHER_CATEGORY


def infer_varietal(product: dict[str, Any]) -> str:
    text = _collect_product_text(product)
    found = [varietal for varietal in KNOWN_VARIETALS if re.search(rf"\b{re.escape(varietal)}\b", text)]
    return ",".join(found) if found else "unknown"


def category_values(category: str) -> set[str]:
    # Split compound category values like "filter roast,espresso roast".
    return {part.strip() for part in category.split(",") if part.strip()}
