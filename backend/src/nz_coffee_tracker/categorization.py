from __future__ import annotations

from html import unescape
from pathlib import Path
import re
from typing import Any

from nz_coffee_tracker.database import (
    get_cached_flavour_notes,
    get_cached_metadata,
    set_cached_flavour_notes,
    set_cached_metadata,
)
from nz_coffee_tracker.llm import (
    compute_content_hash,
    extract_coffee_metadata_llm,
    extract_flavour_notes_llm,
)
from nz_coffee_tracker.ocr import extract_text_from_product_images



FILTER_ROAST = "filter roast"
ESPRESSO_ROAST = "espresso roast"
OMNI_ROAST = "omni roast"
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
    "pink bourbon",
    "red bourbon",
    "yellow bourbon",
    "bourbon",
    "yellow caturra",
    "typica",
    "gesha",
    "geisha",
    "sidra",
    "java",
    "laurina",
    "wush wush",
    "chiroso",
    "papayo",
    "parainema",
    "catimor",
    "sarchimor",
    "san bernardo",
    "sl28",
    "sl34",
    "batian",
    "heirloom",
    "tabi",
    "pacas",
    "villalobos",
    "villa sarchi",
    "villasarchi",
    "aji",
    "p88",
    "s795",
)


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


COUNTRY_MAP = {
    "colombia": "Colombia", "colombian": "Colombia",
    "ethiopia": "Ethiopia", "ethiopian": "Ethiopia",
    "kenya": "Kenya", "kenyan": "Kenya",
    "guatemala": "Guatemala", "guatemalan": "Guatemala",
    "costa rica": "Costa Rica", "costa rican": "Costa Rica",
    "panama": "Panama", "panamanian": "Panama",
    "brazil": "Brazil", "brazilian": "Brazil",
    "indonesia": "Indonesia", "indonesian": "Indonesia",
    "sumatra": "Indonesia", "sumatran": "Indonesia",
    "honduras": "Honduras", "honduran": "Honduras",
    "peru": "Peru", "peruvian": "Peru",
    "rwanda": "Rwanda", "rwandan": "Rwanda",
    "burundi": "Burundi", "burundian": "Burundi",
    "el salvador": "El Salvador", "salvadoran": "El Salvador",
    "nicaragua": "Nicaragua", "nicaraguan": "Nicaragua",
    "mexico": "Mexico", "mexican": "Mexico",
    "papua new guinea": "Papua New Guinea", "png": "Papua New Guinea",
    "yemen": "Yemen", "yemeni": "Yemen",
    "ecuador": "Ecuador", "ecuadorian": "Ecuador",
    "bolivia": "Bolivia", "bolivian": "Bolivia",
    "uganda": "Uganda", "ugandan": "Uganda",
    "tanzania": "Tanzania", "tanzanian": "Tanzania",
    "congo": "DR Congo", "drc": "DR Congo", "dr congo": "DR Congo",
    "china": "China", "chinese": "China",
    "india": "India", "indian": "India",
    "vietnam": "Vietnam", "vietnamese": "Vietnam",
    "thailand": "Thailand", "thai": "Thailand",
    "myanmar": "Myanmar",
    "timor-leste": "East Timor", "east timor": "East Timor",
}


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


CANONICAL_PROCESSES = (
    (r"\bwine\s+yeast\b", "Wine Yeast"),
    (r"\banaerobic\s+natural\b", "Anaerobic Natural"),
    (r"\banaerobic\s+washed\b", "Anaerobic Washed"),
    (r"\banaerobic\s+slow\s+dry\b", "Anaerobic Natural"),
    (r"\basd\s+natural\b", "Anaerobic Natural"),
    (r"\bcarbonic\s+maceration\b", "Carbonic Maceration"),
    (r"\bcarbonic\b", "Carbonic Maceration"),
    (r"\bwashed\s+double\s+ferment(?:ed)?\b", "Washed Double Fermented"),
    (r"\bdouble\s+ferment(?:ed|ation)?\b", "Double Fermented"),
    (r"\bco[-\s]?ferment(?:ed|ation|ing)?\b", "Co-Ferment"),
    (r"\bmosto\s+washed\b", "Mosto Washed"),
    (r"\badvanced\s+washed\b", "Advanced Washed"),
    (r"\bpulped\s+natural\b", "Pulped Natural"),
    (r"\byellow\s+honey\b", "Yellow Honey"),
    (r"\bred\s+honey\b", "Red Honey"),
    (r"\bblack\s+honey\b", "Black Honey"),
    (r"\bhoney\b(?!\s*co[-\s]?ferment)", "Honey"),
    (r"\bwet\s+hulled\b", "Wet Hulled"),
    (r"\bgiling\s+basah\b", "Wet Hulled"),
    (r"\bwashed\s+patio\s+dried\b", "Washed Patio Dried"),
    (r"\bfully\s+washed\b", "Washed"),
    (r"\bwashed\b(?!\s*co[-\s]?ferment|\s*double\s*ferment|\s*patio\s*dried)", "Washed"),
    (r"\bnatural\s+decaf\b", "Natural Decaf"),
    (r"\b(?:sugar\s*cane|sugarcane)(?:\s*ea)?\s*(?:decaf\w*|process\w*|method)?\b", "Sugar Cane Decaf"),
    (r"\bswiss\s*water\s*(?:decaf\w*|process\w*|method)?\b", "Swiss Water Decaf"),
    (r"\bmountain\s*water\s*(?:decaf\w*|process\w*|method)?\b", "Mountain Water Decaf"),
    (r"\bnatural\b(?!\s*co[-\s]?ferment|\s*decaf|\s*sugar\s*cane)", "Natural"),
    (r"\baerobic\b", "Natural"),
    (r"\bdecaf\b", "Decaf"),
)


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


COFFEE_FLAVOUR_LEXICON = (
    "blackcurrant coulis", "lemonade ice block", "mango cheesecake", "white chocolate", "milk chocolate",
    "dark chocolate", "bittersweet chocolate", "hot chocolate", "creamy soda", "grape soda",
    "passionfruit", "turkish delight", "candy apple", "yellow sudan rume", "elderflower",
    "lemon zest", "plum jam", "poached pear", "rooibos tea", "black tea", "chamomile tea",
    "stone fruit", "tropical fruit", "tropical fruits", "red fruit", "dark fruit", "dried fruit",
    "boysenberry ice cream", "boysenberry cupcake", "vanilla syrup", "creamy nougat", "raw honey",
    "floral honey", "chocolate milk", "chocolate-milk", "vanilla custard", "buttery pastry",
    "irish whiskey", "dark currants", "vanilla malt", "soft nougat", "pineapple lumps",
    "orange jaffa", "fruity bubblegum", "myer lemon", "vanilla flower", "rockmelon",
    "cinnamon spice", "dark cocoa", "cinnamon", "molasses", "macadamia", "pistachio",
    "pomelo", "blackcurrant", "blueberry", "blueberries", "blackberry", "blackberries",
    "boysenberry", "raspberry", "raspberries", "strawberry", "strawberries", "cherry",
    "cherries", "apricot", "peach", "plum", "guava", "mango", "papaya", "cola",
    "gumball", "blossom", "florals", "floral", "jasmine", "bergamot", "lime", "lemon",
    "orange", "citrus", "mandarin", "tangelo", "grapefruit", "rhubarb", "currants",
    "caramel", "toffee", "fudge", "honey", "maple syrup", "nougat", "hazelnut",
    "almond", "walnut", "cashew", "peanut", "pecan", "cocoa", "chocolate",
    "clove", "cardamom", "nutmeg", "ginger", "star anise", "raisins", "raisin",
    "marzipan", "brown sugar", "panela", "butterscotch", "malt", "dark rum", "rum", "maple", "toasted spices",
    "dried fig", "fig", "quince", "jammy apple", "green apple", "red apple", "apple",
    "sultana", "sultanas", "redcurrant", "redcurrants", "watermelon", "golden kiwifruit", "kiwifruit", "kiwi",
    "berry jam", "black cherry", "vanilla bean", "vanilla", "cacao nibs", "cacao",
    "dark choc", "milk choc", "marshmallow", "boysenberry yogurt", "yogurt", "yoghurt",
    "rose water", "magnolia flowers", "orange blossom", "white peach", "shortbread",
    "burnt orange", "burnt caramel", "smoked cedar", "peach liqueur", "ginger snap",
    "dried berries", "wine like finish", "orange peel", "oolong tea", "peach jam", "mixed berries",
    "pineapple lollies", "honeysuckle oolong", "white muscat", "apple juice", "jujube date", "orah mandarin",
    "parmesan cheese", "purple grapes"
)

LEXICON_SORTED = sorted(COFFEE_FLAVOUR_LEXICON, key=lambda x: len(x), reverse=True)


def extract_flavour_notes_from_prose(prose: str) -> str:
    found = []
    text_lower = prose.lower()
    for word in LEXICON_SORTED:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            if not any(word in other.lower() for other in found):
                found.append(word.title())
    return ", ".join(found) if found else "unknown"


NON_FLAVOUR_WORDS = {
    "coffee",
    "the coffee",
    "this coffee",
    "our coffee",
    "specialty coffee",
    "espresso",
    "filter",
    "beans",
    "roast",
    "batch",
    "pulping",
    "milling",
    "harvesting",
    "sorting",
    "drying",
    "fermenting",
    "full of flavour",
    "full of flavor",
    "rich, juicy, and full of flavour",
    "rich, juicy, and full of flavor",
}


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


def infer_metadata(
    product: dict[str, Any],
    *,
    database_path: Path | None = None,
    use_llm: bool = True,
) -> dict[str, str]:
    desc = description_text(product)
    title = str(product.get("title", "")).strip()
    content_hash = compute_content_hash(title, desc)
    images = product.get("images") or []
    if not images and product.get("image"):
        images = [product["image"]]

    # 1. Extract rule-based values
    rule_notes = infer_flavour_notes_rule_based(product)
    rule_origin = infer_origin_country_rule_based(product)
    rule_producer = infer_producer_rule_based(product)
    rule_process = infer_process_rule_based(product)
    rule_varietal = infer_varietal_rule_based(product)

    # 3. If product has packaging images or info cards, perform OCR to extract ground-truth tasting notes and metadata
    has_images = bool(product.get("images") or product.get("image"))
    if has_images:
        def _has_resolved_flavour(current_ocr: str) -> bool:
            temp = {"body_html": current_ocr, "title": title}
            return infer_flavour_notes_rule_based(temp) != "unknown"

        ocr_text = extract_text_from_product_images(product, stop_condition=_has_resolved_flavour)
        if ocr_text:
            combined_product = {**product, "body_html": f"{desc}\n{ocr_text}"}
            ocr_only_product = {"body_html": ocr_text, "title": title}
            ocr_notes = infer_flavour_notes_rule_based(ocr_only_product)
            has_explicit_label = extract_description_field(product, ("flavour notes", "flavor notes", "tasting notes", "cupping notes", "cup notes", "cup profile", "flavour profile", "flavor profile", "flavour", "flavor")) != "unknown"
            has_info_card = any("info_card" in (img if isinstance(img, str) else str(img.get("src", ""))).lower() or "card" in (img if isinstance(img, str) else str(img.get("src", ""))).lower() for img in images)
            is_pipe_notes = False
            for line in ocr_text.splitlines():
                if "|" in line and not re.search(r"\b(?:brazil|colombia|ethiopia|kenya|costa\s*rica|indonesia|guatemala|honduras|panama|peru|rwanda|burundi|mexico|washed|natural|honey|espresso|filter|roast|savara|typica|bourbon|caturra|castillo|geisha|gesha|smallholder|factory|society|estate|acidity|body|aftertaste|mouthfeel|finish)\b", line, re.I):
                    if re.search(r"[A-Za-z]{3,}\s*\|\s*[A-Za-z]{3,}", line):
                        is_pipe_notes = True
                        break
            is_card_notes = bool(re.search(r"tasting notes\s*[.:\-]\s*[A-Z]", ocr_text, re.I))
            if ocr_notes != "unknown" and (rule_notes == "unknown" or is_pipe_notes or has_info_card or (not has_explicit_label and is_card_notes)):
                rule_notes = ocr_notes
            elif rule_notes == "unknown":
                rule_notes = infer_flavour_notes_rule_based(combined_product)
            if rule_origin == "unknown":
                rule_origin = infer_origin_country_rule_based(combined_product)
            if rule_process == "unknown":
                rule_process = infer_process_rule_based(combined_product)
            if rule_varietal == "unknown":
                rule_varietal = infer_varietal_rule_based(combined_product)
            desc = f"{desc}\nBag Label OCR: {ocr_text}".strip()

    # 4. Call LLM if enabled, description is substantial, and unstructured metadata needs extraction
    needs_llm = use_llm and len(desc) > 20 and (
        rule_notes == "unknown"
        or (rule_origin == "unknown" and rule_producer == "unknown")
        or (rule_varietal == "unknown" and "blend" not in title.lower())
    )

    llm_meta = extract_coffee_metadata_llm(desc, title=title) if needs_llm else None

    # Validate LLM varietal actually exists in listing text
    varietal_val = rule_varietal
    if varietal_val == "unknown" and llm_meta and llm_meta.get("varietal") and llm_meta["varietal"] != "unknown":
        if llm_meta["varietal"].lower() in f"{title} {desc}".lower():
            varietal_val = llm_meta["varietal"]

    llm_origin = clean_origin_country(llm_meta.get("origin_country") or "") if llm_meta else "unknown"
    llm_process = clean_process(llm_meta.get("process") or "") if llm_meta else "unknown"

    raw_notes = (rule_notes if rule_notes != "unknown" else (llm_meta.get("flavour_notes") if llm_meta and llm_meta.get("flavour_notes") != "unknown" else "unknown")) or "unknown"
    if re.search(r"\bthe\s+browser\b", title, re.IGNORECASE) or "the-browser" in str(product.get("handle", "")).lower():
        raw_notes = "unknown"
    formatted_notes = format_flavour_notes(raw_notes)
    formatted_varietal = format_varietal(varietal_val)

    final_meta = {
        "flavour_notes": formatted_notes,
        "origin_country": (rule_origin if rule_origin != "unknown" else llm_origin) or "unknown",
        "producer": (rule_producer if rule_producer != "unknown" else (llm_meta.get("producer") if llm_meta else "unknown")) or "unknown",
        "process": (rule_process if rule_process != "unknown" else llm_process) or "unknown",
        "varietal": formatted_varietal,
    }

    if database_path is not None:
        set_cached_metadata(content_hash, title, final_meta, database_path)

    return final_meta


def infer_flavour_notes(
    product: dict[str, Any],
    *,
    database_path: Path | None = None,
    use_llm: bool = True,
) -> str:
    return infer_metadata(product, database_path=database_path, use_llm=use_llm)["flavour_notes"]


def infer_origin_country(
    product: dict[str, Any],
    *,
    database_path: Path | None = None,
    use_llm: bool = True,
) -> str:
    return infer_metadata(product, database_path=database_path, use_llm=use_llm)["origin_country"]


def infer_producer(
    product: dict[str, Any],
    *,
    database_path: Path | None = None,
    use_llm: bool = True,
) -> str:
    return infer_metadata(product, database_path=database_path, use_llm=use_llm)["producer"]


def infer_process(
    product: dict[str, Any],
    *,
    database_path: Path | None = None,
    use_llm: bool = True,
) -> str:
    return infer_metadata(product, database_path=database_path, use_llm=use_llm)["process"]


def infer_varietal(
    product: dict[str, Any],
    *,
    database_path: Path | None = None,
    use_llm: bool = True,
) -> str:
    return infer_metadata(product, database_path=database_path, use_llm=use_llm)["varietal"]


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
    desc = description_text(product)
    desc_lower = desc.lower()

    # Manual overrides: Slow Coffee Raspberry Kiss is espresso roast only
    if ("raspberry kiss" in title_lower or "raspberry-kiss" in handle_lower) and (
        source == "slowcoffee.co.nz" or not source or "slow" in handle_lower
    ):
        return ESPRESSO_ROAST

    # 1. PRIORITY 1: Check Shopify Tags
    has_tag_omni = any(t in ("extraction-omni", "omni roast", "omni", "omni-roast", "extraction:omni") for t in tags_lower)
    has_tag_filter = any(
        t in ("extraction-filter", "filter roast", "filter brewing", "quiz-filter", "clarity", "filter", "filter coffee")
        or "brew method:filter" in t
        for t in tags_lower
    )
    has_tag_espresso = any(
        t in ("extraction-espresso", "modern-espresso", "single espresso roast", "quiz-espresso", "espresso blend", "espresso-blend", "espresso program", "house", "espresso", "espresso coffee")
        or "brew method:espresso" in t
        for t in tags_lower
    )

    if has_tag_omni:
        return OMNI_ROAST

    # If both filter and espresso tags are present
    if has_tag_filter and has_tag_espresso:
        # Check if description explicitly clarifies it as espresso (e.g. single origin with rogue filter tag)
        if re.search(r"\broasted\s+for\s+espresso\b|\bpart\s+of\s+espresso\s+program\b", desc_lower) and collection_handle and "espresso" in collection_handle.lower():
            return ESPRESSO_ROAST
        return OMNI_ROAST

    if has_tag_filter:
        return FILTER_ROAST

    if has_tag_espresso:
        return ESPRESSO_ROAST

    # 2. PRIORITY 2: Title & Handle explicit roast markers
    if re.search(r"\bomni\s*roast\b|espresso\s*\/\s*filter|filter\s*\/\s*espresso", title_lower) or "omni-roast" in handle_lower:
        return OMNI_ROAST

    has_title_filter = bool(re.search(r"\bfilter\s*roast\b|\(filter\)|\[[^\]]*filter[^\]]*\]|\bfilter\s*coffee\b", title_lower) or "filter-roast" in handle_lower)
    has_title_espresso = bool(re.search(r"\bespresso\s*roast\b|\(espresso\)|\[[^\]]*espresso[^\]]*\]|\bespresso\s*blend\b|\bespresso\s*subscription\b", title_lower) or "espresso-roast" in handle_lower or "espresso-blend" in handle_lower)

    if has_title_filter and has_title_espresso:
        return OMNI_ROAST
    if has_title_filter:
        return FILTER_ROAST
    if has_title_espresso:
        return ESPRESSO_ROAST

    # 3. PRIORITY 3: Collection Context
    has_col_filter = False
    has_col_espresso = False
    if collection_handle:
        col = collection_handle.lower().strip()
        if col in (
            "filter",
            "filter-coffee",
            "filter-extraction",
            "single-origin-coffees",
            "specialty-coffee-beans-nz",
            "single-origin",
            "single-origins",
            "clarity",
        ):
            has_col_filter = True
        elif col in (
            "espresso",
            "espresso-coffee",
            "espresso-blends",
            "espresso-offerings-1",
            "espresso-blends-decaf",
            "house-blends",
            "blends",
            "espresso-program",
            "house",
            "modern",
        ):
            has_col_espresso = True

    # 4. PRIORITY 4: Description & Recommended Brewing / Suitability / Roast Profile
    has_desc_omni = bool(re.search(r"\bomni\s*roast\b|\bomni\b|espresso\s*(?:and|&|\/)\s*filter|filter\s*(?:and|&|\/)\s*espresso|shines\s+as\s+much\s+for\s+filter\b", desc_lower))
    has_desc_filter = False
    has_desc_espresso = False

    rec_match = re.search(
        r"(?:recommended\s*(?:use|brew(?:ing)?|methods?)?|suti?ab\w*|best\s*(?:for|brewed)|suggested\s*brewing|most\s*suited\s*for)\s*[:\-]?\s*(.*?)(?=\s+(?:origin|producer|farm|estate|process|flavou?r|tasting|altitude|variety|characteristics)|$|[.;|\n])",
        desc_lower,
    )
    if rec_match:
        rec_content = rec_match.group(1)
        rec_has_esp = bool(re.search(r"\bespresso|pressuri[sz]ed\b", rec_content))
        rec_has_flt = bool(re.search(r"\b(?:filter|pour\s*over|v60|chemex|aeropress|plunger|french\s*press|drip|batch)\b", rec_content))
        if "if you prefer a darker" in desc_lower or "if you prefer a roastier" in desc_lower:
            rec_has_flt = False

        if rec_has_esp and rec_has_flt:
            has_desc_omni = True
        elif rec_has_esp:
            has_desc_espresso = True
        elif rec_has_flt:
            has_desc_filter = True

    if re.search(r"\broasted\s+for\s+espresso\b|\bpart\s+of\s+espresso\s+program\b|\bespresso\s+program\b|\broast\s*profile\s*[:\-]\s*medium\s*\/\s*espresso\b", desc_lower):
        has_desc_espresso = True

    if re.search(r"\bfor\s+(?:a\s+)?filter\s+roast\b|\bdelicious\s+filter\b|\broast\s*level\s*[:\-]\s*light\b", desc_lower):
        has_desc_filter = True

    # Combine collection & description indicators
    if has_desc_omni or (has_col_filter and has_col_espresso) or ((has_col_filter or has_desc_filter) and (has_col_espresso or has_desc_espresso)):
        return OMNI_ROAST
    if has_col_filter or has_desc_filter:
        return FILTER_ROAST
    if has_col_espresso or has_desc_espresso:
        return ESPRESSO_ROAST

    # 5. PRIORITY 5: Final Fallback Heuristics (Product Type / Blend)
    if (
        "blend" in title_lower
        or "blend" in tags_str
        or p_type_lower in ("coffee house", "house", "blend")
    ):
        return ESPRESSO_ROAST
    if (
        "single origin" in tags_str
        or "single-origin" in tags_str
        or p_type_lower in ("single origin", "single origin specialty coffee", "coffee clarity", "coffee vibrant")
    ):
        return FILTER_ROAST

    return OTHER_CATEGORY


def category_values(category: str) -> set[str]:
    # Split compound category values like "filter roast,espresso roast".
    return {part.strip() for part in category.split(",") if part.strip()}
