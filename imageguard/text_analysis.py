"""OCR and text pattern analysis."""

from __future__ import annotations

import codecs
import re
from typing import Dict, List, Optional, Tuple

from PIL import Image

from .patterns import DEFAULT_PATTERNS, Pattern, find_matches


# Leetspeak character mappings (character -> possible leetspeak representations)
LEETSPEAK_MAP = {
    "a": ["4", "@", "^", "/\\"],
    "b": ["8", "|3", "13"],
    "c": ["(", "<", "{"],
    "e": ["3"],
    "g": ["6", "9"],
    "h": ["#", "|-|"],
    "i": ["1", "!", "|", "l"],
    "l": ["1", "|", "7"],
    "o": ["0"],
    "s": ["5", "$"],
    "t": ["7", "+"],
    "z": ["2"],
}

# Reverse mapping for decoding (leetspeak char -> original)
LEETSPEAK_REVERSE = {}
for char, leets in LEETSPEAK_MAP.items():
    for leet in leets:
        LEETSPEAK_REVERSE[leet] = char


def decode_rot13(text: str) -> str:
    """Decode ROT13 encoded text."""
    return codecs.decode(text, "rot_13")


def decode_leetspeak(text: str) -> str:
    """Decode leetspeak to regular text.

    Handles common substitutions like: 1gn0r3 -> ignore, 5y5t3m -> system
    """
    result = text.lower()

    # Sort by length descending to match longer patterns first
    sorted_leets = sorted(LEETSPEAK_REVERSE.keys(), key=len, reverse=True)

    for leet in sorted_leets:
        result = result.replace(leet, LEETSPEAK_REVERSE[leet])

    return result


def detect_obfuscated_text(text: str) -> Dict[str, any]:
    """Detect and decode ROT13 and leetspeak obfuscation.

    Returns dict with:
        - has_obfuscation: bool
        - rot13_decoded: str (if ROT13 patterns found)
        - leetspeak_decoded: str (if leetspeak patterns found)
        - obfuscation_score: float (0.0 - 1.0)
    """
    result = {
        "has_obfuscation": False,
        "rot13_decoded": None,
        "leetspeak_decoded": None,
        "obfuscation_score": 0.0,
    }

    # Check for leetspeak patterns (numbers/symbols mixed with letters)
    leetspeak_pattern = r"[a-zA-Z]*[0-9@$#!|<>{}^]+[a-zA-Z]*"
    leetspeak_matches = re.findall(leetspeak_pattern, text)

    # Count leetspeak-like substitutions
    leet_char_count = sum(1 for c in text if c in "0134567@$#!|<>{}^")
    alpha_count = sum(1 for c in text if c.isalpha())
    total_relevant = leet_char_count + alpha_count

    if total_relevant > 0:
        leet_ratio = leet_char_count / total_relevant
        if leet_ratio > 0.1 and leetspeak_matches:  # At least 10% leet chars
            decoded = decode_leetspeak(text)
            if decoded != text.lower():
                result["leetspeak_decoded"] = decoded
                result["has_obfuscation"] = True
                result["obfuscation_score"] = max(result["obfuscation_score"], min(1.0, leet_ratio * 2))

    # Check for ROT13 by looking for common words after decoding
    # Only apply to text that looks like it could be ROT13 (mostly alphabetic)
    if alpha_count > 10:
        rot13_decoded = decode_rot13(text)
        # Check if decoded text contains common injection keywords
        injection_keywords = [
            "ignore", "system", "prompt", "instruction", "bypass",
            "forget", "disregard", "pretend", "role", "jailbreak"
        ]
        original_lower = text.lower()
        decoded_lower = rot13_decoded.lower()

        # Count keywords in original vs decoded
        orig_keyword_count = sum(1 for kw in injection_keywords if kw in original_lower)
        decoded_keyword_count = sum(1 for kw in injection_keywords if kw in decoded_lower)

        # If decoding reveals more keywords, it's likely ROT13 encoded
        if decoded_keyword_count > orig_keyword_count:
            result["rot13_decoded"] = rot13_decoded
            result["has_obfuscation"] = True
            result["obfuscation_score"] = max(
                result["obfuscation_score"],
                min(1.0, decoded_keyword_count * 0.25)
            )

    return result


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


def calculate_text_score(
    extracted_text: str,
    matched_patterns: List[Pattern],
    image_area: int,
    density_threshold: float = 5e-4,
    obfuscation_result: Optional[Dict] = None,
) -> float:
    # Moderate base contribution per matched pattern to avoid saturating at 1.0.
    base_score = 0.25 * len(matched_patterns)

    text_density = len(extracted_text.strip()) / float(image_area) if image_area else 0.0
    if text_density > density_threshold:
        base_score += 0.1 * (text_density / density_threshold)

    if contains_imperative_structure(extracted_text):
        base_score += 0.15

    # Add obfuscation score contribution
    if obfuscation_result and obfuscation_result.get("has_obfuscation"):
        base_score += 0.2 * obfuscation_result.get("obfuscation_score", 0.0)

    return min(1.0, base_score)


def analyze_text(
    image: Image.Image,
    image_area: int,
    languages: Optional[List[str]] = None,
    patterns: Optional[List[Pattern]] = None,
    include_text: bool = True,
    max_text_length: int = 10000,
    detect_obfuscation: bool = True,
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

    # Check for obfuscated text (ROT13, leetspeak)
    obfuscation_result = None
    additional_matches = []
    if detect_obfuscation and extracted_text.strip():
        obfuscation_result = detect_obfuscated_text(extracted_text)

        # If obfuscation detected, also check decoded text for patterns
        if obfuscation_result.get("has_obfuscation"):
            decoded_texts = []
            if obfuscation_result.get("rot13_decoded"):
                decoded_texts.append(obfuscation_result["rot13_decoded"])
            if obfuscation_result.get("leetspeak_decoded"):
                decoded_texts.append(obfuscation_result["leetspeak_decoded"])

            for decoded in decoded_texts:
                matches = find_matches(decoded, patterns=patterns)
                for m in matches:
                    if m.id not in [am.id for am in additional_matches]:
                        additional_matches.append(m)

    matched = find_matches(extracted_text, patterns=patterns)
    # Combine original matches with matches from decoded text
    all_matched = matched + [m for m in additional_matches if m.id not in [om.id for om in matched]]

    score = calculate_text_score(extracted_text, all_matched, image_area, obfuscation_result=obfuscation_result)

    display_text = extracted_text.strip()
    if not include_text:
        display_text = ""
    elif max_text_length and len(display_text) > max_text_length:
        display_text = display_text[: max_text_length] + "..."

    details = {
        "text_found": bool(extracted_text.strip()),
        "extracted_text": display_text,
        "patterns_matched": [m.id for m in all_matched],
        "confidence": confidence,
    }

    # Add obfuscation details if detected
    if obfuscation_result and obfuscation_result.get("has_obfuscation"):
        details["obfuscation"] = {
            "detected": True,
            "rot13_decoded": obfuscation_result.get("rot13_decoded"),
            "leetspeak_decoded": obfuscation_result.get("leetspeak_decoded"),
            "obfuscation_score": obfuscation_result.get("obfuscation_score", 0.0),
        }

    return {
        "score": score,
        "details": details,
    }
