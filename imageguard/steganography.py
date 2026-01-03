"""Steganography detection heuristics (Phase 4)."""

from __future__ import annotations

import math
from typing import Dict

import numpy as np
from PIL import Image


def _to_gray_array(image: Image.Image) -> np.ndarray:
    return np.array(image.convert("L"))


def lsb_analysis(gray: np.ndarray) -> Dict:
    lsb = gray & 1
    ones_ratio = float(lsb.mean())
    if ones_ratio in (0.0, 1.0):
        entropy = 0.0
    else:
        entropy = -ones_ratio * math.log2(ones_ratio) - (1.0 - ones_ratio) * math.log2(1.0 - ones_ratio)
    randomness_score = min(1.0, max(0.0, entropy))
    pattern_detected = randomness_score < 0.7 or ones_ratio < 0.1 or ones_ratio > 0.9
    return {
        "randomness_score": randomness_score,
        "pattern_detected": pattern_detected,
        "ones_ratio": ones_ratio,
    }


def chi_square_test(gray: np.ndarray) -> Dict:
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    chi_sq = 0.0
    for i in range(0, 256, 2):
        observed = hist[i]
        expected = (hist[i] + hist[i + 1]) / 2.0
        if expected > 0:
            chi_sq += (observed - expected) ** 2 / expected
    df = 127
    # Normal approximation for chi-square distribution (df large).
    z = (chi_sq - df) / math.sqrt(2 * df)
    p_value = 0.5 * math.erfc(z / math.sqrt(2))
    is_significant = p_value < 0.05
    return {"p_value": float(p_value), "is_significant": is_significant}


def rs_analysis(gray: np.ndarray, group_size: int = 4) -> Dict:
    flat = gray.flatten()
    if len(flat) < group_size:
        return {"rs_ratio": 0.0, "embedding_detected": False}
    usable = flat[: len(flat) - (len(flat) % group_size)]
    groups = usable.reshape(-1, group_size)

    def smoothness(group: np.ndarray) -> float:
        return float(np.sum(np.abs(np.diff(group.astype(int)))))

    def flip_lsb(group: np.ndarray) -> np.ndarray:
        return group ^ 1

    regular = 0
    singular = 0
    for group in groups:
        f_orig = smoothness(group)
        f_flip = smoothness(flip_lsb(group))
        if f_flip > f_orig:
            regular += 1
        elif f_flip < f_orig:
            singular += 1

    total = regular + singular
    if total == 0:
        rs_ratio = 0.0
    else:
        rs_ratio = (regular - singular) / total
    embedding_detected = abs(rs_ratio) < 0.1 and total > 100
    return {"rs_ratio": float(rs_ratio), "embedding_detected": embedding_detected}


def spa_analysis(gray: np.ndarray) -> Dict:
    lsb = gray & 1
    diffs = lsb[:, 1:] != lsb[:, :-1]
    diff_ratio = float(diffs.mean()) if diffs.size else 0.0
    # Heuristic: closer to 0.5 implies higher embedding rate.
    estimated_embedding_rate = min(1.0, max(0.0, (diff_ratio - 0.25) / 0.25))
    return {"estimated_embedding_rate": estimated_embedding_rate, "lsb_diff_ratio": diff_ratio}


def analyze_steganography(
    image: Image.Image,
    lsb_enabled: bool = True,
    chi_square_enabled: bool = True,
    rs_enabled: bool = True,
    spa_enabled: bool = False,
) -> Dict:
    gray = _to_gray_array(image)

    details = {}
    scores = []

    if lsb_enabled:
        lsb_res = lsb_analysis(gray)
        details["lsb_analysis"] = lsb_res
        scores.append(lsb_res["randomness_score"])

    if chi_square_enabled:
        chi_res = chi_square_test(gray)
        details["chi_square_test"] = chi_res
        scores.append(1.0 if chi_res["is_significant"] else 0.0)

    if rs_enabled:
        rs_res = rs_analysis(gray)
        details["rs_analysis"] = rs_res
        rs_score = max(0.0, 1.0 - min(1.0, abs(rs_res["rs_ratio"]) / 0.5))
        scores.append(rs_score)

    if spa_enabled:
        spa_res = spa_analysis(gray)
        details["spa_analysis"] = spa_res
        scores.append(spa_res["estimated_embedding_rate"])

    score = sum(scores) / len(scores) if scores else 0.0
    score = max(0.0, min(1.0, score))

    return {"score": score, "details": details}
