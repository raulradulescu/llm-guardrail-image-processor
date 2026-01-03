"""Structural analysis (Phase 5)."""

from __future__ import annotations

from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

from .patterns import Pattern, find_matches


def _pil_to_cv(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def detect_qr_codes(image: np.ndarray) -> Dict:
    detector = cv2.QRCodeDetector()
    decoded = []
    points = None
    try:
        # OpenCV 4+ multi-detect
        if hasattr(detector, "detectAndDecodeMulti"):
            ok, data_list, pts, _ = detector.detectAndDecodeMulti(image)
            if ok:
                decoded = [d for d in data_list if d]
                points = pts
        else:
            data, pts, _ = detector.detectAndDecode(image)
            if data:
                decoded = [data]
                points = pts
    except Exception:
        decoded = []
        points = None
    return {
        "found": bool(decoded),
        "count": len(decoded),
        "decoded_content": decoded,
        "points": points.tolist() if points is not None else [],
    }


def detect_barcodes(image: np.ndarray) -> Dict:
    try:
        from pyzbar import pyzbar
    except Exception:
        return {
            "found": False,
            "count": 0,
            "types": [],
            "decoded_content": [],
            "status": "unavailable",
        }
    barcodes = pyzbar.decode(image)
    decoded = []
    types = []
    for b in barcodes:
        try:
            data = b.data.decode("utf-8", errors="ignore")
        except Exception:
            data = str(b.data)
        decoded.append(data)
        types.append(getattr(b, "type", "unknown"))
    return {
        "found": bool(decoded),
        "count": len(decoded),
        "types": types,
        "decoded_content": decoded,
        "status": "ok",
    }


def screenshot_heuristics(gray: np.ndarray) -> Dict:
    h, w = gray.shape
    aspect = w / h if h else 0.0
    common_ratios = [16 / 9, 9 / 16, 4 / 3, 3 / 4]
    aspect_match = any(abs(aspect - r) < 0.15 for r in common_ratios)

    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=min(w, h) // 4, maxLineGap=10)
    line_count = 0 if lines is None else len(lines)

    # Count horizontal lines near top/bottom for UI bars.
    top_bar = False
    bottom_bar = False
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            if abs(y1 - y2) < 4:
                if y1 < h * 0.1:
                    top_bar = True
                if y1 > h * 0.9:
                    bottom_bar = True

    # Count rectangle-like contours for UI elements.
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects = 0
    for c in contours:
        x, y, rw, rh = cv2.boundingRect(c)
        if rw * rh < 200:
            continue
        if 2 < rw / max(rh, 1) < 20:
            rects += 1

    detected_ui = []
    confidence = 0.0
    if aspect_match:
        detected_ui.append("aspect_ratio_match")
        confidence += 0.2
    if line_count > 10:
        detected_ui.append("straight_lines")
        confidence += 0.2
    if top_bar:
        detected_ui.append("top_bar")
        confidence += 0.2
    if bottom_bar:
        detected_ui.append("bottom_bar")
        confidence += 0.1
    if rects > 6:
        detected_ui.append("rectangular_ui_elements")
        confidence += 0.3

    is_screenshot = confidence >= 0.5
    screenshot_type = "ui" if is_screenshot else None
    return {
        "is_screenshot": is_screenshot,
        "confidence": min(1.0, confidence),
        "detected_ui_elements": detected_ui,
        "screenshot_type": screenshot_type,
    }


def detect_text_overlay(gray: np.ndarray) -> Dict:
    edges = cv2.Canny(gray, 50, 150)
    dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    overlay_regions = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w < 20 or h < 8:
            continue
        if w / max(h, 1) < 2:
            continue
        if w * h > (gray.shape[0] * gray.shape[1]) * 0.1:
            continue
        overlay_regions.append({"x": x, "y": y, "w": w, "h": h})

    synthetic_text_detected = len(overlay_regions) > 6
    return {
        "synthetic_text_detected": synthetic_text_detected,
        "overlay_regions": overlay_regions[:20],
        "compression_inconsistency": False,
    }


def analyze_structural(
    image: Image.Image,
    enable_qr: bool = True,
    enable_barcodes: bool = True,
    enable_screenshots: bool = True,
    analyze_decoded_content: bool = True,
    patterns: Optional[List[Pattern]] = None,
) -> Dict:
    cv_img = _pil_to_cv(image)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    qr = detect_qr_codes(cv_img) if enable_qr else {"found": False, "count": 0, "decoded_content": []}
    barcodes = detect_barcodes(cv_img) if enable_barcodes else {"found": False, "count": 0, "types": [], "decoded_content": []}

    decoded_payloads = []
    decoded_payloads.extend(qr.get("decoded_content", []))
    decoded_payloads.extend(barcodes.get("decoded_content", []))
    contains_injection = False
    if analyze_decoded_content and decoded_payloads:
        for payload in decoded_payloads:
            if find_matches(payload, patterns=patterns):
                contains_injection = True
                break
    qr["contains_injection"] = contains_injection if qr.get("found") else False

    screenshot = screenshot_heuristics(gray) if enable_screenshots else {"is_screenshot": False, "confidence": 0.0}
    text_overlay = detect_text_overlay(gray)

    score = 0.0
    if qr.get("found") or barcodes.get("found"):
        score += 0.3
    if contains_injection:
        score += 0.4
    if screenshot.get("is_screenshot"):
        score += 0.3 * screenshot.get("confidence", 0.0)
    if text_overlay.get("synthetic_text_detected"):
        score += 0.2

    score = max(0.0, min(1.0, score))

    return {
        "score": score,
        "details": {
            "qr_codes": qr,
            "barcodes": barcodes,
            "screenshot_analysis": screenshot,
            "text_overlay_analysis": text_overlay,
        },
    }
