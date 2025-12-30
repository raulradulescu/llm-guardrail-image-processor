"""OCR and text pattern analysis."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from PIL import Image

from .patterns import DEFAULT_PATTERNS, Pattern, find_matches


def run_ocr(image: Image.Image, languages: Optional[List[str]] = None, psm: int = 6) -> Tuple[str, float]:
    """Run pytesseract OCR; returns extracted text and average confidence (best-effort)."""
    try:
        import pytesseract
    except Exception as exc:
        raise RuntimeError("pytesseract not available") from exc

    lang_str = "+".join(languages) if languages else "eng"
    config = f"--psm {psm}"
    text = pytesseract.image_to_string(image, lang=lang_str, config=config)

    try:
        data = pytesseract.image_to_data(image, lang=lang_str, config=config, output_type=pytesseract.Output.DICT)
        confs = [float(c) for c in data.get("conf", []) if c and float(c) >= 0]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
    except Exception:
        avg_conf = 0.0
    return text, avg_conf


def contains_imperative_structure(text: str) -> bool:
    imperative_markers = [
        r"\bignore\b",
        r"\bdisregard\b",
        r"\bforget\b",
        r"\bfrom now on\b",
        r"\byou must\b",
        r"\byou will\b",
        r"\bdo not\b",
    ]
    pattern = re.compile("|".join(imperative_markers), re.IGNORECASE)
    return bool(pattern.search(text))


def calculate_text_score(extracted_text: str, matched_patterns: List[Pattern], image_area: int, density_threshold: float = 5e-4) -> float:
    # Moderate base contribution per matched pattern to avoid saturating at 1.0.
    base_score = 0.25 * len(matched_patterns)

    text_density = len(extracted_text.strip()) / float(image_area) if image_area else 0.0
    if text_density > density_threshold:
        base_score += 0.1 * (text_density / density_threshold)

    if contains_imperative_structure(extracted_text):
        base_score += 0.15

    return min(1.0, base_score)


def analyze_text(
    image: Image.Image,
    image_area: int,
    languages: Optional[List[str]] = None,
    patterns: Optional[List[Pattern]] = None,
    include_text: bool = True,
    max_text_length: int = 10000,
) -> Dict:
    """Perform OCR and pattern analysis, returning module details."""
    # Try multiple PSM modes: 6 (block of text) and 11 (sparse text).
    extracted_text = ""
    confidence = 0.0
    for psm in (6, 11):
        text, conf = run_ocr(image, languages=languages, psm=psm)
        if len(text.strip()) > len(extracted_text.strip()):
            extracted_text, confidence = text, conf
        if conf > 70 and text.strip():
            break

    matched = find_matches(extracted_text, patterns=patterns)
    score = calculate_text_score(extracted_text, matched, image_area)

    display_text = extracted_text.strip()
    if not include_text:
        display_text = ""
    elif max_text_length and len(display_text) > max_text_length:
        display_text = display_text[: max_text_length] + "..."

    return {
        "score": score,
        "details": {
            "text_found": bool(extracted_text.strip()),
            "extracted_text": display_text,
            "patterns_matched": [m.id for m in matched],
            "confidence": confidence,
        },
    }
