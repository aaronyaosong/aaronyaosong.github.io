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


def infer_varietal(product: dict[str, Any]) -> str:
    text = _collect_product_text(product)
    found = [varietal for varietal in KNOWN_VARIETALS if re.search(rf"\b{re.escape(varietal)}\b", text)]
    return ",".join(found) if found else "unknown"


def category_values(category: str) -> set[str]:
    # Split compound category values like "filter roast,espresso roast".
    return {part.strip() for part in category.split(",") if part.strip()}
