from __future__ import annotations

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

from nz_coffee_tracker.categorization.utils import description_text, extract_description_field
from nz_coffee_tracker.categorization.extractors.flavour import infer_flavour_notes_rule_based, format_flavour_notes
from nz_coffee_tracker.categorization.extractors.origin import infer_origin_country_rule_based, clean_origin_country
from nz_coffee_tracker.categorization.extractors.producer import infer_producer_rule_based
from nz_coffee_tracker.categorization.extractors.process import infer_process_rule_based, clean_process
from nz_coffee_tracker.categorization.extractors.varietal import infer_varietal_rule_based, format_varietal

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

