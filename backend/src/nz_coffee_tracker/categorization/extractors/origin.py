from __future__ import annotations

import re
from typing import Any

from nz_coffee_tracker.categorization.constants import COUNTRY_MAP
from nz_coffee_tracker.categorization.utils import _collect_product_text, extract_description_field

def clean_origin_country(text: str) -> str:
    if not text:
        return "unknown"
    text_lower = text.lower()
    # Specific New Zealand grown lots
    if re.search(r"\b(?:pekerau|pekerau hills|whakatane)\b", text_lower):
        return "New Zealand"

    # Filter out NZ roaster headquarters references
    if re.search(r"\b(?:new zealand|aotearoa|auckland|wellington|hamilton|christchurch|dunedin|h-town|italy)\b", text_lower):
        # Remove those specific words before checking country
        text_lower = re.sub(r"\b(?:new zealand|aotearoa(?: nz)?|auckland|wellington|hamilton|christchurch|dunedin|h-town|italy)\b", " ", text_lower)
    found: list[str] = []
    for word, country in COUNTRY_MAP.items():
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            if country not in found:
                found.append(country)
    return ", ".join(found) if found else "unknown"


def infer_origin_country_rule_based(product: dict[str, Any]) -> str:
    # 1. Check title first for clear origin
    title = str(product.get("title", ""))
    title_country = clean_origin_country(title)
    if title_country != "unknown":
        return title_country

    # 2. Check labeled origin field
    labeled = extract_description_field(product, ("origin", "origin country", "country", "location"))
    if labeled and labeled != "unknown":
        cleaned = clean_origin_country(labeled)
        if cleaned != "unknown":
            return cleaned

    # 3. Check entire text
    full_text = _collect_product_text(product)
    return clean_origin_country(full_text)

