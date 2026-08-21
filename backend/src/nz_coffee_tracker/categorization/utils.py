from __future__ import annotations

import re
from html import unescape
from typing import Any

def _normalize_text(raw: str) -> str:
    compact = re.sub(r"\s+", " ", raw).strip().lower()
    return compact


def description_text(product: dict[str, Any]) -> str:
    raw = str(product.get("body_html") or product.get("description") or "")
    if not raw:
        return ""
    # Convert breaks and block elements to newlines
    text = re.sub(r"<\s*br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(
        r"</?(?:p|div|h[1-6]|li|ul|ol|tr|table|blockquote|header|section|article)[^>]*>",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    # Normalize whitespace per line and collapse excessive newlines
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def _collect_product_text(product: dict[str, Any]) -> str:
    title = str(product.get("title", ""))
    desc = description_text(product)
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags_text = tags
    elif isinstance(tags, (list, tuple)):
        tags_text = " ".join(str(t) for t in tags)
    else:
        tags_text = ""
    return f"{title} {desc} {tags_text}".lower()


def extract_description_field(product: dict[str, Any], labels: tuple[str, ...]) -> str:
    text = description_text(product)
    label_pattern = "|".join(re.escape(label) for label in labels)
    next_label = r"origin(?: country)?|country|location|producer|producers|farm|estate|process(?:ing)?|process method|processing method|fermentation|flavou?r notes|tasting notes|cupping notes|cup notes|cup profile|tasting card|notes|variety|varieties|varietal|varietals|variedad|the coffee|brewing recipe|brew guide|filter recipe|espresso recipe|suggested method|dose|recipe|altitude|elevation|region|province|colony|roast|roast profile|roast level|roast style|suitable for|importer|exporter|years used|recommended use|recomending use|roaster\'s comment|about the coffee|characteristics|body|acidity|finish|r\s*egion"

    # 1. Line start / header boundary with colon/dash/em-dash/dot delimiter (supports line and multiline & continuation)
    match = re.search(
        rf"(?:^|\n)\s*(?<!full of\s)(?<!rich\s)(?<!packed with\s)(?:{label_pattern})\b\s*[:\-–—.]\s*(?:\n\s*)?([A-Z0-9][^\n]*(?:\n\s*(?:&|and|,)\s*[^\n]+)?)(?=\s+(?:{next_label})\s*[:\-–—.]|\s+(?:variedad|the coffee|brewing recipe|brew guide|digital tasting card|recommended use|recomending use|roaster\'s comment|about the coffee|score|disclaimer)\b|$|[;|\n])",
        text,
        re.IGNORECASE,
    )
    if match and match.group(1).strip():
        val = match.group(1).strip()
        first_word = val.split()[0] if val.split() else ""
        if not re.search(r"^(?:of|for|that|which|with|an?|the|and|is|are|nursery|seedlings)$", first_word, re.I):
            return val

    # 2. Line start / structured label with optional separator or whitespace (e.g. C4 cards, Atomic characteristics, Slow spec rows)
    match_line = re.search(
        rf"(?:^|\n)\s*(?<!full of\s)(?<!rich\s)(?<!packed with\s)(?:{label_pattern})\b\s*[:\-–—.]?\s*(?:\n\s*)?([A-Z0-9][^\n]{{2,120}}?)(?=\s+(?:{next_label})\s*[:\-–—.]|\s+(?:variedad|the coffee|brewing recipe|brew guide|digital tasting card|recommended use|recomending use|body|acidity|finish|roaster\'s comment|about the coffee)\b|$|[;|\n])",
        text,
        re.IGNORECASE,
    )
    if match_line and match_line.group(1).strip():
        val = match_line.group(1).strip()
        first_word = val.split()[0] if val.split() else ""
        if not re.search(r"^(?:of|for|that|which|with|an?|the|and|is|are|nursery|seedlings)$", first_word, re.I):
            return val

    return "unknown"

