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


def _preprocess_for_ocr(image: Image.Image, method: str = "default") -> Image.Image:
    """Apply preprocessing to improve OCR accuracy."""
    from PIL import ImageOps, ImageFilter, ImageEnhance

    img = image.convert("RGB")

    if method == "default":
        return img
    elif method == "grayscale":
        return ImageOps.grayscale(img)
    elif method == "contrast":
        gray = ImageOps.grayscale(img)
        return ImageEnhance.Contrast(gray).enhance(2.0)
    elif method == "threshold_light":
        # For light text on varying backgrounds
        gray = ImageOps.grayscale(img)
        return gray.point(lambda x: 255 if x > 180 else 0)
    elif method == "threshold_dark":
        # For dark text
        gray = ImageOps.grayscale(img)
        return gray.point(lambda x: 255 if x < 100 else 0)
    elif method == "invert_threshold":
        # Invert then threshold - good for semi-transparent overlays
        gray = ImageOps.grayscale(img)
        inverted = ImageOps.invert(gray)
        return inverted.point(lambda x: 255 if x > 50 else 0)
    elif method == "sharpen":
        return img.filter(ImageFilter.SHARPEN)

    return img


def _extract_regions(image: Image.Image) -> List[Tuple[Image.Image, str]]:
    """Extract key regions where overlay text commonly appears."""
    regions = []
    w, h = image.size

    # Full image
    regions.append((image, "full"))

    # Top strip (common for overlay text)
    top_height = min(60, h // 5)
    if top_height > 20:
        regions.append((image.crop((0, 0, w, top_height)), "top"))

    # Bottom strip
    bottom_height = min(60, h // 5)
    if bottom_height > 20:
        regions.append((image.crop((0, h - bottom_height, w, h)), "bottom"))

    # Top-left corner
    corner_size = min(100, w // 3, h // 3)
    if corner_size > 30:
        regions.append((image.crop((0, 0, corner_size, corner_size)), "top_left"))

    return regions


def run_enhanced_ocr(
    image: Image.Image,
    languages: Optional[List[str]] = None,
    scale_factor: int = 3,
) -> Tuple[str, float, Dict]:
    """Enhanced OCR with multiple preprocessing passes and region analysis.

    Returns:
        Tuple of (combined_text, confidence, details_dict)
    """
    try:
        import pytesseract
    except Exception as exc:
        raise RuntimeError("pytesseract not available") from exc

    lang_str = "+".join(languages) if languages else "eng"
    all_texts = []
    best_confidence = 0.0
    region_results = {}

    # Preprocessing methods to try
    preprocess_methods = [
        "default", "contrast", "threshold_light",
        "invert_threshold", "sharpen"
    ]

    # PSM modes: 6=block, 7=single line, 11=sparse, 12=sparse with OSD
    psm_modes = [6, 7, 11]

    # Extract and process regions
    regions = _extract_regions(image)

    for region_img, region_name in regions:
        region_texts = set()

        # Scale up for better OCR
        scaled = region_img.resize(
            (region_img.width * scale_factor, region_img.height * scale_factor),
            Image.LANCZOS
        )

        for method in preprocess_methods:
            processed = _preprocess_for_ocr(scaled, method)

            for psm in psm_modes:
                try:
                    config = f"--psm {psm}"
                    text = pytesseract.image_to_string(
                        processed, lang=lang_str, config=config
                    ).strip()

                    # Filter out garbage (very short or mostly non-alpha)
                    if text and len(text) >= 3:
                        alpha_ratio = sum(c.isalpha() or c.isspace() for c in text) / len(text)
                        if alpha_ratio > 0.5:
                            region_texts.add(text)

                            # Get confidence for this result
                            try:
                                data = pytesseract.image_to_data(
                                    processed, lang=lang_str, config=config,
                                    output_type=pytesseract.Output.DICT
                                )
                                confs = [float(c) for c in data.get("conf", []) if c and float(c) >= 0]
                                conf = sum(confs) / len(confs) if confs else 0.0
                                best_confidence = max(best_confidence, conf)
                            except Exception:
                                pass
                except Exception:
                    continue

        if region_texts:
            # Combine unique texts from this region
            combined = " | ".join(sorted(region_texts, key=len, reverse=True)[:3])
            region_results[region_name] = combined
            all_texts.extend(region_texts)

    # Combine all unique text findings
    unique_texts = list(set(all_texts))
    # Sort by length (longer = more complete)
    unique_texts.sort(key=len, reverse=True)

    # Take top results and combine
    combined_text = "\n".join(unique_texts[:5]) if unique_texts else ""

    return combined_text, best_confidence, {"regions": region_results}


def _clean_ocr_text(text: str) -> str:
    """Clean OCR text for better pattern matching."""
    # Remove common OCR noise characters
    cleaned = re.sub(r'[|~=\-_<>{}^\[\]\\]+', ' ', text)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Remove very short isolated characters (OCR artifacts)
    cleaned = re.sub(r'\s[a-zA-Z]\s', ' ', cleaned)
    return cleaned.strip()


def _extract_sentences(text: str) -> List[str]:
    """Extract coherent sentence-like segments from noisy OCR text."""
    # Split by common separators
    segments = re.split(r'[|\n]+', text)
    sentences = []
    for seg in segments:
        cleaned = _clean_ocr_text(seg)
        # Keep segments that look like actual sentences (have multiple words)
        word_count = len([w for w in cleaned.split() if len(w) > 1])
        if word_count >= 3:
            sentences.append(cleaned)
    return sentences


def contains_imperative_structure(text: str) -> bool:
    imperative_markers = [
        r"\bignore\b",
        r"\bdisregard\b",
        r"\bforget\b",
        r"\bfrom now on\b",
        r"\byou must\b",
        r"\byou will\b",
        r"\bdo not\b",
        r"\bjust\s+output\b",
        r"\bwhen\s+asked\b",
        r"\balways\s+(say|respond|output)\b",
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
    use_enhanced_ocr: bool = True,
) -> Dict:
    """Perform OCR and pattern analysis, returning module details."""
    extracted_text = ""
    confidence = 0.0
    ocr_details = {}

    if use_enhanced_ocr:
        # Use enhanced OCR with multi-pass preprocessing
        extracted_text, confidence, ocr_details = run_enhanced_ocr(
            image, languages=languages, scale_factor=3
        )
    else:
        # Fallback to basic OCR with multiple PSM modes
        for psm in (6, 11):
            text, conf = run_ocr(image, languages=languages, psm=psm)
            if len(text.strip()) > len(extracted_text.strip()):
                extracted_text, confidence = text, conf
            if conf > 70 and text.strip():
                break

    # Clean text for better pattern matching
    cleaned_text = _clean_ocr_text(extracted_text)
    text_sentences = _extract_sentences(extracted_text)

    # Check for obfuscated text (ROT13, leetspeak)
    obfuscation_result = None
    additional_matches = []
    if detect_obfuscation and extracted_text.strip():
        obfuscation_result = detect_obfuscated_text(cleaned_text)

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

    # Match patterns against cleaned text and individual sentences
    matched = find_matches(cleaned_text, patterns=patterns)
    for sentence in text_sentences:
        sentence_matches = find_matches(sentence, patterns=patterns)
        for m in sentence_matches:
            if m.id not in [om.id for om in matched]:
                matched.append(m)

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

    # Add region-specific OCR results if available
    if ocr_details and ocr_details.get("regions"):
        details["ocr_regions"] = ocr_details["regions"]

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
