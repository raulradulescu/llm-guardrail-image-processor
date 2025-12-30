"""Hidden/obfuscated text detection (Phase 2)."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image

from .patterns import Pattern, find_matches
from .text_analysis import run_ocr


THRESHOLDS: Sequence[int] = (50, 100, 150, 200, 250)


def pil_to_cv_gray(image: Image.Image) -> np.ndarray:
    """Convert PIL RGB image to grayscale CV image."""
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)


def apply_clahe(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def multi_threshold_ocr(gray: np.ndarray, languages: Optional[List[str]], thresholds: Sequence[int] | None = None) -> Tuple[List[str], List[int]]:
    texts: List[str] = []
    used_thresholds: List[int] = []
    for t in (thresholds or THRESHOLDS):
        _, binary = cv2.threshold(gray, t, 255, cv2.THRESH_BINARY)
        pil_img = Image.fromarray(binary)
        text, _ = run_ocr(pil_img, languages=languages, psm=11)
        if text.strip():
            texts.append(text.strip())
            used_thresholds.append(t)
    return texts, used_thresholds


def per_channel_ocr(image: Image.Image, languages: Optional[List[str]]) -> Tuple[List[str], List[str]]:
    texts: List[str] = []
    channels_used: List[str] = []
    r, g, b = image.split()
    for name, channel in (("r", r), ("g", g), ("b", b)):
        text, _ = run_ocr(channel, languages=languages, psm=11)
        if text.strip():
            texts.append(text.strip())
            channels_used.append(name)
    return texts, channels_used


def edge_density_flags(gray: np.ndarray, grid: int = 4, threshold: float = 0.15) -> int:
    edges = cv2.Canny(gray, 50, 150)
    h, w = edges.shape
    cell_h, cell_w = h // grid, w // grid
    flagged = 0
    for i in range(grid):
        for j in range(grid):
            cell = edges[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]
            density = np.count_nonzero(cell) / float(cell.size)
            if density > threshold:
                flagged += 1
    return flagged


def analyze_hidden_text(
    image: Image.Image,
    image_area: int,
    languages: Optional[List[str]] = None,
    patterns: Optional[List[Pattern]] = None,
    thresholds: Sequence[int] | None = None,
) -> Dict:
    gray = pil_to_cv_gray(image)
    enhanced = apply_clahe(gray)

    base_text, _ = run_ocr(image, languages=languages, psm=6)
    base_text = base_text.strip()

    threshold_texts, used_thresholds = multi_threshold_ocr(enhanced, languages=languages, thresholds=thresholds)
    channel_texts, channels_used = per_channel_ocr(image, languages=languages)

    all_hidden_texts = [t for t in threshold_texts + channel_texts if t and t not in base_text]
    combined_text = "\n".join(all_hidden_texts).strip()

    matched = find_matches(combined_text or base_text, patterns=patterns)

    # Heuristic scoring: hidden text presence + pattern severity + edge density.
    score = 0.0
    if combined_text:
        score += 0.25
    score += 0.15 * len(matched)

    flagged_cells = edge_density_flags(enhanced)
    score += min(0.1, 0.02 * flagged_cells)

    score = min(1.0, score)

    display_text = combined_text
    return {
        "score": score,
        "details": {
            "text_found": bool(combined_text),
            "extracted_text": display_text,
            "patterns_matched": [m.id for m in matched],
            "thresholds_tried": used_thresholds,
            "channels_used": channels_used,
            "edge_cells_flagged": flagged_cells,
        },
    }
