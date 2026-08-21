from __future__ import annotations

import re
from typing import Any

from nz_coffee_tracker.categorization.constants import CANONICAL_PROCESSES
from nz_coffee_tracker.categorization.utils import description_text, extract_description_field

def clean_process(text: str) -> str:
    if not text:
        return "unknown"
    text_lower = text.lower()
    found: list[str] = []
    
    # 1. Dynamic Co-Ferment Check
    co_ferment_matches = re.finditer(r"\b([a-z]+(?:\s+[a-z]+){0,2}\s+(?:honey|washed|natural|aerobic|anaerobic)?\s*co[-\s]?ferment(?:ed|ation|ing)?)\b", text_lower)
    for m in co_ferment_matches:
        val = m.group(1).title()
        val = re.sub(r"Co[-\s]?Ferment(?:ed|ation|ing)?", "Co-Ferment", val)
        val = val.replace(" Co Ferment", " Co-Ferment")
        if val not in found:
            found.append(val)
            
    # Check standalone co-ferment if no dynamic matched
    if not found and re.search(r"\bco[-\s]?ferment(?:ed|ation|ing)?\b", text_lower):
        found.append("Co-Ferment")

    for pattern, canonical in CANONICAL_PROCESSES:
        if re.search(pattern, text_lower):
            # Do not add base processes if they are part of a dynamic co-ferment we already found
            if canonical in ("Honey", "Washed", "Natural", "Anaerobic Natural", "Anaerobic Washed"):
                if any(canonical.lower() in f.lower() and "co-ferment" in f.lower() for f in found):
                    continue

            if canonical not in found:
                if any(k in canonical for k in ("Sugar Cane Decaf", "Swiss Water Decaf", "Mountain Water Decaf", "Natural Decaf")) and "Decaf" in found:
                    found.remove("Decaf")
                is_subsumed = any(canonical in existing for existing in found if existing != canonical) or \
                              (canonical == "Decaf" and any("Decaf" in p for p in found)) or \
                              (canonical == "Honey" and any("Honey" in p for p in found)) or \
                              (canonical == "Natural" and any("Natural" in p for p in found)) or \
                              (canonical == "Washed" and any("Washed" in p for p in found))
                if not is_subsumed:
                    found.append(canonical)
    return ", ".join(found) if found else "unknown"

def infer_process_rule_based(product: dict[str, Any]) -> str:
    title = str(product.get("title", ""))
    desc = description_text(product)

    # 1. Check title bracket tag e.g. [washed], [natural], [washed double fermented]
    match = re.search(r"\[([^\]]*(?:washed|natural|honey|anaerobic|aerobic|ferment|carbonic|decaf)[^\]]*)\]", title, re.IGNORECASE)
    if match:
        cleaned = clean_process(match.group(1))
        if cleaned != "unknown":
            return cleaned

    # 2. Check labeled process field
    labeled = extract_description_field(product, ("process", "processing", "processing method", "process method", "process/variety"))
    if labeled and labeled != "unknown":
        cleaned = clean_process(labeled)
        if cleaned != "unknown":
            return cleaned

    # 3. Check title directly
    cleaned_title = clean_process(title)
    if cleaned_title != "unknown":
        return cleaned_title

    # 4. Check tags
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags_text = tags
    elif isinstance(tags, (list, tuple)):
        tags_text = " ".join(str(t) for t in tags)
    else:
        tags_text = ""
    if tags_text:
        cleaned = clean_process(tags_text)
        if cleaned != "unknown":
            return cleaned

    return "unknown"

