from __future__ import annotations

import re
from typing import Any

from nz_coffee_tracker.categorization.utils import extract_description_field

def infer_producer_rule_based(product: dict[str, Any]) -> str:
    labeled = extract_description_field(product, ("producer", "farm", "estate", "station", "washing station", "grower"))
    if labeled and labeled != "unknown":
        # Keep short producer names, strip recipe/altitude noise if present
        cleaned = re.sub(r"\s+(?:altitude|region|harvest|roast|brew|recipe|dose|variety|varietal)\b.*$", "", labeled, flags=re.IGNORECASE).strip()
        if cleaned and len(cleaned) <= 60:
            return cleaned
    title = str(product.get("title", "")).strip()
    if " - " in title:
        prefix = title.split(" - ")[0].strip()
        if not re.search(r"\b(?:decaf|espresso|filter|omni|blend|roast)\b", prefix, re.IGNORECASE) and 2 < len(prefix) <= 50:
            return prefix
    return "unknown"

