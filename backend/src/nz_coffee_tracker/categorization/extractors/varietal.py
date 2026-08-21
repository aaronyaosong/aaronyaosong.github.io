from __future__ import annotations

import re
from typing import Any

from nz_coffee_tracker.categorization.constants import KNOWN_VARIETALS
from nz_coffee_tracker.categorization.utils import _collect_product_text, extract_description_field

def format_varietal(raw: str) -> str:
    if not raw or raw == "unknown" or re.search(r"\b(?:country|farm|process|processing|recipe|brewing|method|roaster|region|altitude|producer)\b", raw, re.I):
        return "unknown"
    cleaned = re.sub(r"^mixed\s*\((.*?)\)$", r"\1", raw.strip(), flags=re.I)
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    titled = []
    for p in parts:
        if re.match(r"^sl\s*\d+$", p, re.I):
            titled.append(re.sub(r"sl\s*", "SL", p, flags=re.I))
        elif re.match(r"^ruiru\s*\d+$", p, re.I):
            titled.append(re.sub(r"ruiru\s*", "Ruiru ", p, flags=re.I))
        elif re.match(r"^jarc\s*\d+$", p, re.I):
            titled.append(re.sub(r"jarc\s*", "JARC ", p, flags=re.I))
        else:
            titled.append(p.title())
    return ", ".join(titled) if titled else "unknown"

def infer_varietal_rule_based(product: dict[str, Any]) -> str:
    labeled = extract_description_field(product, ("varietal", "variety", "varieties grown", "varieties", "varietals", "variedad"))
    if labeled and labeled != "unknown" and len(labeled) <= 90:
        cleaned = format_varietal(labeled)
        if cleaned != "unknown":
            return cleaned
    text = _collect_product_text(product)
    found = [varietal for varietal in KNOWN_VARIETALS if re.search(rf"\b{re.escape(varietal)}\b", text)]
    filtered = [v for v in found if not any(v.lower() != other.lower() and v.lower() in other.lower() for other in found)]
    return format_varietal(",".join(filtered)) if filtered else "unknown"

