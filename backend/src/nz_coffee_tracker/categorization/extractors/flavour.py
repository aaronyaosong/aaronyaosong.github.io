from __future__ import annotations

import re
from typing import Any

from nz_coffee_tracker.categorization.constants import LEXICON_SORTED, NON_FLAVOUR_WORDS
from nz_coffee_tracker.categorization.utils import description_text, extract_description_field

def format_flavour_notes(raw: str) -> str:
    if not raw or raw == "unknown" or "full of flavo" in raw.lower():
        return "unknown"
    if "Black:" in raw and "Milk:" in raw:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        formatted_parts = []
        for part in parts:
            if ":" in part:
                label, val = part.split(":", 1)
                formatted_parts.append(f"{label.strip().title()}: {format_flavour_notes(val.strip())}")
            else:
                formatted_parts.append(format_flavour_notes(part))
        return " | ".join(formatted_parts)
    # Strip trailing punctuation, ellipses, quotes
    cleaned = re.sub(r"[…\.\,\:\;\s\—\-\"]+$", "", raw).strip()
    cleaned = re.sub(r"^[,\s:—\-\"]+", "", cleaned).strip()
    parts = re.split(r",\s*|\s+&\s+|\s+and\s+|\s*/\s*|\s*\|\s*", cleaned)
    titled = []
    for p in parts:
        item = p.strip().rstrip(".…")
        if item and len(item) > 1 and item.lower() not in NON_FLAVOUR_WORDS:
            titled_val = item.title()
            titled_val = re.sub(r"'S\b", "'s", titled_val)
            titled.append(titled_val)
    return ", ".join(titled) if titled else "unknown"

def extract_flavour_notes_from_prose(prose: str) -> str:
    found = []
    text_lower = prose.lower()
    for word in LEXICON_SORTED:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            if not any(word in other.lower() for other in found):
                found.append(word.title())
    return ", ".join(found) if found else "unknown"

def _clean_flavour_string(raw: str) -> str:
    cleaned = re.sub(r"^[,\s:—\-]+", "", raw).strip()
    cleaned = re.sub(r"[,\s:—\-]+$", "", cleaned).strip()
    cleaned = re.sub(r"^(?:with\s+a\s+|a\s+|an\s+|the\s+|rich\s+|sweet\s+|fresh\s+|notes\s+of\s+|flavou?rs\s+of\s+|hints\s+of\s+|expect\s+)", "", cleaned, flags=re.I)
    cleaned = re.split(r"\s+(?:to\s+create|bringing|making|roasted\s+in|roasted\s+for|grown|and\s+a\s+silky|and\s+a\s+smooth|and\s+a\s+delicate|and\s+a\s+velvety|and\s+a\s+creamy|with\s+a\s+(?:silky|smooth|delicate|velvety|creamy|bright|lingering)\s+(?:mouthfeel|body|acidity|texture)|recom[a-z]*\s*use)\b", cleaned, flags=re.I)[0]
    result = re.sub(r"\s+", " ", cleaned).strip().rstrip(",;.")
    if result.lower() in NON_FLAVOUR_WORDS or len(result) < 3:
        return ""
    return result

def infer_flavour_notes_rule_based(product: dict[str, Any]) -> str:
    title = str(product.get("title", "")).strip()
    if re.search(r"\bthe\s+browser\b", title, re.IGNORECASE) or "the-browser" in str(product.get("handle", "")).lower():
        return "unknown"

    # 1. Split Espresso Profile (e.g. Eternal Coffee: '- Black: Peach Milk Candy, Mixed Berries\n- Milk: Citrus, Peach, Mixed Berries')
    text = description_text(product)
    match_split = re.search(
        r"(?:^|\n)\s*(?:[-*•]\s*)?black\s*[:\-–—]\s*([^\n]+?)\s*(?:^|\n)\s*(?:[-*•]\s*)?milk\s*[:\-–—]\s*([^\n]+?)(?=\s+(?:origin|producer|farm|region|process|variet|altitude|elevation)|$|\n\n)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match_split:
        black_cleaned = _clean_flavour_string(match_split.group(1).strip())
        milk_cleaned = _clean_flavour_string(match_split.group(2).strip())
        if black_cleaned and milk_cleaned:
            return f"Black: {format_flavour_notes(black_cleaned)} | Milk: {format_flavour_notes(milk_cleaned)}"

    # 2. Explicit field labels (including 'cupping notes', 'flavour notes', 'flavor notes', 'tasting notes', 'flavour profile', 'flavor profile', 'flavour', 'flavor', 'notes')
    labeled = extract_description_field(product, ("flavour notes", "flavor notes", "tasting notes", "cupping notes", "cup notes", "cup profile", "flavour profile", "flavor profile", "notes", "flavour", "flavor"))
    if labeled and labeled != "unknown" and len(labeled) > 2:
        if not re.search(r"^(?:of\s+this\s+coffee|are\s+as\s+follows|below)", labeled, re.I):
            if re.search(r"\b(?:expect|aromas?\s+of|with\s+(?:jammy|sweet|caramel|lingering|a\s+soft)|sweetness\s+then|notes\s+shine|wrapped\s+in|syrupy\s+body)\b", labeled, re.I):
                prose_extracted = extract_flavour_notes_from_prose(labeled)
                if prose_extracted != "unknown":
                    return prose_extracted
            cleaned = _clean_flavour_string(labeled)
            if cleaned:
                return cleaned

    if not text:
        return "unknown"

    # 3. Leading tasting notes line before metadata headers (e.g. Eternal Coffee: 'Boysenberry Yogurt, Pink Pomelo, Golden Kiwifruit\n\nProducer:...')
    next_meta = r"producer|origin(?: country)?|farm|estate|process(?:ing)?|process method|varietal|variety|region|altitude|elevation"
    match_leading = re.search(
        rf"^\s*([A-Z][^.:\n]{{3,80}})\s*(?:\n+)\s*(?:{next_meta})\s*[:\-–—.]",
        text,
        re.IGNORECASE,
    )
    if match_leading:
        cleaned = _clean_flavour_string(match_leading.group(1))
        if cleaned and not re.search(r"\b(?:roast(?:ed)?|blend|specialty|limited|welcome|introducing|experience)\b", cleaned, re.I):
            return cleaned

    # 4. Pipe-separated notes line (e.g. Embassy Blend bag label: 'APPLE CRUMBLE | VANILLA CUSTARD | DATES')
    match_pipe = re.search(r"^([^\n|:]+\s*\|\s*[^\n|:]+(?:\s*\|\s*[^\n|:]+)*)$", text, re.M)
    if match_pipe:
        cleaned = _clean_flavour_string(match_pipe.group(1))
        if cleaned and not re.search(r"\b(?:roast(?:ed)?|specialty|coffee|brazil|colombia|natural|washed|espresso|filter)\b", cleaned, re.I):
            return cleaned

    # 4. 'In the cup: ...' / 'In the cup we taste: ...'
    match_cup = re.search(
        r"(?:in\s+(?:the\s+)?cup(?:\s*we\s+taste|\s*we\s+get|\s*expect|\s*features)?)\s*[:\-]?\s*([^.;\n]+)",
        text,
        re.IGNORECASE,
    )
    if match_cup and match_cup.group(1).strip() and len(match_cup.group(1).strip()) > 3:
        cleaned = _clean_flavour_string(match_cup.group(1))
        if cleaned:
            return cleaned

    # 4. 'flavours/favours of ...', 'notes of ...', 'tastes of ...', 'hints of ...'
    for match_flavours in re.finditer(
        r"(?:flavou?rs?|favou?rs?|notes?|tastes?|hints?|aroma\s*&\s*flavou?rs?)\s+(?:of|include)\s*[:\-–—.]?\s*([\s\S]+?)(?=\n\s*(?:origin|process|roast\s*profile|espresso\s*recipe|dose|yield|time|altitude|variety|varietal|producer|brew|whole\s*beans|ground|specialit?y\s*(?:light|medium|dark)?\s*roast)\b|\n\n|\.\s+[A-Z]|$)",
        text,
        re.IGNORECASE,
    ):
        raw_val = " ".join(match_flavours.group(1).split())
        cleaned = _clean_flavour_string(raw_val)
        if cleaned:
            return cleaned

    # 5. 'layered and indulgent — ...', 'layers of ...'
    match_layers = re.search(
        r"(?:layered\s+and\s+indulgent|layers\s+of|rich\s+layers\s+of)\s*[:\-—]\s*([^.;\n]+)",
        text,
        re.IGNORECASE,
    )
    if match_layers and match_layers.group(1).strip():
        cleaned = _clean_flavour_string(match_layers.group(1))
        if cleaned:
            return cleaned

    # 6. 'expect ...'
    match_expect = re.search(
        r"(?:expect)\s+(?:a\s+)?([^.;\n]+?)(?=\.\s+|\s*—|\s+roasted\s+for|\s+brought\s+to\s+us|$)",
        text,
        re.IGNORECASE,
    )
    if match_expect and match_expect.group(1).strip():
        cleaned = _clean_flavour_string(match_expect.group(1))
        if cleaned:
            return cleaned

    # 7. 'blends/combines X and Y flavours'
    match_blend = re.search(
        r"(?:blends?|combines?)\s+([^.;\n]+?)\s+(?:flavou?rs?|notes?)",
        text,
        re.IGNORECASE,
    )
    if match_blend and match_blend.group(1).strip():
        cleaned = _clean_flavour_string(match_blend.group(1))
        if cleaned:
            return cleaned

    # 8. Coffee Lexicon extraction fallback
    found = []
    text_lower = text.lower()
    for word in LEXICON_SORTED:
        if word in ("cherry", "cherries"):
            matches = list(re.finditer(rf"\b{re.escape(word)}\b", text_lower))
            is_valid = False
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(text_lower), m.end() + 45)
                window = text_lower[start:end]
                if re.search(
                    r"(?:every|the|all|ripe|coffee|red|fresh|whole|harvest(?:ed)?|pick(?:ed)?|sort(?:ed)?|pulp(?:ed)?|wash(?:ed)?|ferment(?:ed)?|dri(?:ed)?|float(?:ing)?)\s+(?:coffee\s+)?cher(?:ry|ries)"
                    r"|cher(?:ry|ries)\s+(?:is|are|were|was)?\s*(?:handpicked|hand-picked|picked|harvested|sorted|pulped|washed|fermented|dried|hand|processed|delivered|floated|undergo)",
                    window,
                ):
                    continue
                is_valid = True
                break
            if not is_valid:
                continue
        elif word == "honey" and re.search(r"\bhoney\s+(?:process|processed|anaerobic|natural|washed)\b", text_lower):
            matches = list(re.finditer(r"\bhoney\b", text_lower))
            is_valid = False
            for m in matches:
                start = max(0, m.start() - 15)
                end = min(len(text_lower), m.end() + 20)
                window = text_lower[start:end]
                if re.search(r"\bhoney\s+(?:process|processed|anaerobic)\b", window) or re.search(r"\b(?:yellow|red|black|white)\s+honey\b", window):
                    continue
                is_valid = True
                break
            if not is_valid:
                continue

        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            if not any(word in other for other in found):
                found.append(word.title())
    if found:
        return ", ".join(found[:4])

    return "unknown"

