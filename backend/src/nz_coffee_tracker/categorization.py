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
    "bourbon",
    "typica",
    "gesha",
    "geisha",
    "sidra",
    "java",
    "sl28",
    "sl34",
    "batian",
    "heirloom",
    "tabi",
    "pacas",
    "villalobos",
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
    next_label = r"origin(?: country)?|country|producer|farm|estate|process(?:ing)?|flavou?r notes|tasting notes|notes|variety|varietal"
    match = re.search(
        rf"(?:{label_pattern})\s*[:\-]\s*(.*?)(?=\s+(?:{next_label})\s*[:\-]|$|[.;|\n])",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else "unknown"


def infer_origin_country_rule_based(product: dict[str, Any]) -> str:
    labeled = extract_description_field(product, ("origin", "origin country", "country"))
    if labeled and labeled != "unknown":
        return labeled
    text = f"{product.get('title', '')} {description_text(product)}".lower()
    country_map = {
        "ethiopia": "Ethiopia", "ethiopian": "Ethiopia",
        "colombia": "Colombia", "colombian": "Colombia",
        "kenya": "Kenya", "kenyan": "Kenya",
        "guatemala": "Guatemala", "guatemalan": "Guatemala",
        "costa rica": "Costa Rica", "costa rican": "Costa Rica",
        "panama": "Panama", "panamanian": "Panama",
        "honduras": "Honduras", "honduran": "Honduras",
        "brazil": "Brazil", "brazilian": "Brazil",
        "rwanda": "Rwanda", "rwandan": "Rwanda",
        "peru": "Peru", "peruvian": "Peru",
        "ecuador": "Ecuador", "ecuadorian": "Ecuador",
        "el salvador": "El Salvador", "salvadoran": "El Salvador",
        "burundi": "Burundi", "burundian": "Burundi",
        "uganda": "Uganda", "ugandan": "Uganda",
        "indonesia": "Indonesia", "indonesian": "Indonesia", "sumatra": "Indonesia", "sumatran": "Indonesia",
        "papua new guinea": "Papua New Guinea",
        "mexico": "Mexico", "mexican": "Mexico",
        "tanzania": "Tanzania", "tanzanian": "Tanzania",
        "nicaragua": "Nicaragua", "nicaraguan": "Nicaragua",
    }
    for word, country in country_map.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return country
    return "unknown"


def infer_producer_rule_based(product: dict[str, Any]) -> str:
    labeled = extract_description_field(product, ("producer", "farm", "estate", "station", "washing station", "grower"))
    if labeled and labeled != "unknown":
        return labeled
    title = str(product.get("title", "")).strip()
    if " - " in title:
        prefix = title.split(" - ")[0].strip()
        if not re.search(r"\b(?:decaf|espresso|filter|omni|blend|roast)\b", prefix, re.IGNORECASE) and len(prefix) > 2:
            return prefix
    return "unknown"


def infer_process_rule_based(product: dict[str, Any]) -> str:
    labeled = extract_description_field(product, ("process", "processing", "processing method"))
    if labeled and labeled != "unknown":
        return labeled
    text = f"{product.get('title', '')} {description_text(product)}".lower()
    match = re.search(r"\[([^\]]*(?:washed|natural|honey|anaerobic|ferment)[^\]]*)\]", str(product.get("title", "")), re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    for proc in ("anaerobic natural", "anaerobic washed", "double fermented", "carbonic maceration", "natural", "washed", "honey", "wet hulled"):
        if re.search(rf"\b{re.escape(proc)}\b", text):
            return proc.title()
    return "unknown"


def infer_varietal_rule_based(product: dict[str, Any]) -> str:
    text = _collect_product_text(product)
    found = [varietal for varietal in KNOWN_VARIETALS if re.search(rf"\b{re.escape(varietal)}\b", text)]
    return ",".join(found) if found else "unknown"


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
    "marzipan", "brown sugar", "panela", "butterscotch", "malt",
)


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
}


def _clean_flavour_string(raw: str) -> str:
    cleaned = re.sub(r"^[,\s:—\-]+", "", raw).strip()
    cleaned = re.sub(r"[,\s:—\-]+$", "", cleaned).strip()
    cleaned = re.sub(r"^(?:with\s+a\s+|a\s+|an\s+|the\s+|rich\s+|sweet\s+|fresh\s+|notes\s+of\s+|flavou?rs\s+of\s+|hints\s+of\s+|expect\s+)", "", cleaned, flags=re.I)
    cleaned = re.split(r"\s+(?:to\s+create|bringing|making|with\s+a|roasted\s+in|roasted\s+for|grown|and\s+a\s+silky|and\s+a\s+smooth|and\s+a\s+delicate|and\s+a\s+velvety|and\s+a\s+creamy|recom[a-z]*\s*use)\b", cleaned, flags=re.I)[0]
    result = re.sub(r"\s+", " ", cleaned).strip().rstrip(",;.")
    if result.lower() in NON_FLAVOUR_WORDS or len(result) < 3:
        return ""
    return result


def infer_flavour_notes_rule_based(product: dict[str, Any]) -> str:
    # 1. Explicit field labels
    labeled = extract_description_field(product, ("flavour notes", "flavor notes", "tasting notes", "notes"))
    if labeled and labeled != "unknown" and len(labeled) > 2:
        if not re.search(r"^(?:of\s+this\s+coffee|are\s+as\s+follows|below)", labeled, re.I):
            cleaned = _clean_flavour_string(labeled)
            if cleaned:
                return cleaned

    text = description_text(product)
    if not text:
        return "unknown"

    # 2. 'In the cup: ...' / 'In the cup we taste: ...'
    match_cup = re.search(
        r"(?:in\s+(?:the\s+)?cup(?:\s*we\s+taste|\s*we\s+get|\s*expect|\s*features)?)\s*[:\-]?\s*([^.;\n]+)",
        text,
        re.IGNORECASE,
    )
    if match_cup and match_cup.group(1).strip() and len(match_cup.group(1).strip()) > 3:
        cleaned = _clean_flavour_string(match_cup.group(1))
        if cleaned:
            return cleaned

    # 3. 'flavours/favours of ...', 'notes of ...', 'tastes of ...', 'hints of ...'
    for match_flavours in re.finditer(
        r"(?:flavou?rs?|favou?rs?|notes?|tastes?|hints?|aroma\s*&\s*flavou?rs?)\s+(?:of|include)\s+([^.;\n]+?)(?=\.\s+|\s+roasted\s+in|\s+grown|\s+process|\s+origin|$)",
        text,
        re.IGNORECASE,
    ):
        cleaned = _clean_flavour_string(match_flavours.group(1))
        if cleaned:
            return cleaned

    # 4. 'layered and indulgent — ...', 'layers of ...'
    match_layers = re.search(
        r"(?:layered\s+and\s+indulgent|layers\s+of|rich\s+layers\s+of)\s*[:\-—]\s*([^.;\n]+)",
        text,
        re.IGNORECASE,
    )
    if match_layers and match_layers.group(1).strip():
        cleaned = _clean_flavour_string(match_layers.group(1))
        if cleaned:
            return cleaned

    # 5. 'expect ...'
    match_expect = re.search(
        r"(?:expect)\s+(?:a\s+)?([^.;\n]+?)(?=\.\s+|\s*—|\s+roasted\s+for|\s+brought\s+to\s+us|$)",
        text,
        re.IGNORECASE,
    )
    if match_expect and match_expect.group(1).strip():
        cleaned = _clean_flavour_string(match_expect.group(1))
        if cleaned:
            return cleaned

    # 6. 'blends/combines X and Y flavours'
    match_blend = re.search(
        r"(?:blends?|combines?)\s+([^.;\n]+?)\s+(?:flavou?rs?|notes?)",
        text,
        re.IGNORECASE,
    )
    if match_blend and match_blend.group(1).strip():
        cleaned = _clean_flavour_string(match_blend.group(1))
        if cleaned:
            return cleaned

    # 7. Coffee Lexicon extraction fallback
    found = []
    text_lower = text.lower()
    for word in COFFEE_FLAVOUR_LEXICON:
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

    # 1. Check persistent SQLite cache first
    if database_path is not None:
        cached = get_cached_metadata(content_hash, database_path)
        if (
            cached
            and cached.get("flavour_notes")
            and cached["flavour_notes"] != "unknown"
            and (cached.get("origin_country", "unknown") != "unknown" or cached.get("process", "unknown") != "unknown" or cached.get("producer", "unknown") != "unknown")
        ):
            return {
                "flavour_notes": cached.get("flavour_notes") or "unknown",
                "origin_country": cached.get("origin_country") or "unknown",
                "producer": cached.get("producer") or "unknown",
                "process": cached.get("process") or "unknown",
                "varietal": cached.get("varietal") or "unknown",
            }

    # 2. Extract rule-based values
    rule_notes = infer_flavour_notes_rule_based(product)
    rule_origin = infer_origin_country_rule_based(product)
    rule_producer = infer_producer_rule_based(product)
    rule_process = infer_process_rule_based(product)
    rule_varietal = infer_varietal_rule_based(product)

    # 3. Call LLM if enabled, description is substantial, and unstructured metadata needs extraction
    needs_llm = use_llm and len(desc) > 20 and (
        rule_notes == "unknown"
        or (rule_origin == "unknown" and rule_producer == "unknown")
    )

    llm_meta = extract_coffee_metadata_llm(desc, title=title) if needs_llm else None

    # Validate LLM varietal actually exists in listing text
    llm_varietal = "unknown"
    if llm_meta and llm_meta.get("varietal") and llm_meta["varietal"] != "unknown":
        if llm_meta["varietal"].lower() in f"{title} {desc}".lower():
            llm_varietal = llm_meta["varietal"].lower()

    final_meta = {
        "flavour_notes": (rule_notes if rule_notes != "unknown" else (llm_meta.get("flavour_notes") if llm_meta and llm_meta.get("flavour_notes") != "unknown" else "unknown")) or "unknown",
        "origin_country": (rule_origin if rule_origin != "unknown" else (llm_meta.get("origin_country") if llm_meta else "unknown")) or "unknown",
        "producer": (rule_producer if rule_producer != "unknown" else (llm_meta.get("producer") if llm_meta else "unknown")) or "unknown",
        "process": (rule_process if rule_process != "unknown" else (llm_meta.get("process") if llm_meta else "unknown")) or "unknown",
        "varietal": (rule_varietal if rule_varietal != "unknown" else llm_varietal) or "unknown",
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
