"""Frequency domain analysis (Phase 3)."""

from __future__ import annotations

import math
from typing import Dict, Optional

import cv2
import numpy as np

try:
    import pywt
except Exception:  # pragma: no cover - optional dependency
    pywt = None


def pil_to_gray_f(image) -> np.ndarray:
    import numpy as np  # local import to avoid circular
    from PIL import Image

    if isinstance(image, Image.Image):
        arr = np.array(image.convert("L"))
    else:
        arr = image
    return arr.astype(np.float32) / 255.0


def fft_anomaly(gray: np.ndarray, threshold: float = 0.7) -> Dict:
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    mag = np.abs(fshift)
    # Central low-frequency region
    h, w = mag.shape
    center_h, center_w = h // 2, w // 2
    radius = min(center_h, center_w) // 4

    y, x = np.ogrid[:h, :w]
    mask = (x - center_w) ** 2 + (y - center_h) ** 2 <= radius**2
    low_energy = mag[mask].sum() + 1e-8
    high_energy = mag[~mask].sum() + 1e-8
    ratio = high_energy / (low_energy + high_energy)
    # Map ratio to score with a soft threshold
    denom = max(1e-6, 1.0 - threshold)
    score = max(0.0, min(1.0, (ratio - threshold) / denom))
    return {"score": score, "high_freq_ratio": ratio}


def dct_anomaly(gray: np.ndarray, threshold: float = 0.6) -> Dict:
    # Convert to 8x8 blocks like JPEG.
    h, w = gray.shape
    h8, w8 = h - (h % 8), w - (w % 8)
    gray = gray[:h8, :w8]
    blocks = gray.reshape(h8 // 8, 8, w8 // 8, 8).swapaxes(1, 2).reshape(-1, 8, 8)
    if blocks.size == 0:
        return {"score": 0.0, "hf_lf_ratio": 0.0}
    hf_energy = []
    lf_energy = []
    for block in blocks:
        dct = cv2.dct(block)
        # low-frequency coefficients: top-left 2x2
        lf = np.abs(dct[:2, :2]).mean()
        # high-frequency coefficients: rest
        hf = np.abs(dct[2:, 2:]).mean()
        hf_energy.append(hf)
        lf_energy.append(lf)
    lf_mean = np.mean(lf_energy) + 1e-6
    hf_mean = np.mean(hf_energy)
    ratio = hf_mean / (hf_mean + lf_mean)
    denom = max(1e-6, 1.0 - threshold)
    score = max(0.0, min(1.0, (ratio - threshold) / denom))
    return {"score": score, "hf_lf_ratio": ratio}


def wavelet_anomaly(gray: np.ndarray, threshold: float = 0.5, wavelet_type: str = "haar", levels: int = 1) -> Dict:
    if pywt is None:
        return {"score": 0.0, "enabled": False}
    coeffs = pywt.wavedec2(gray, wavelet_type, level=levels)
    cA = coeffs[0]
    details = coeffs[1:]
    detail_energy = sum(np.abs(c).mean() for level in details for c in level)
    approx_energy = np.abs(cA).mean() + 1e-6
    ratio = detail_energy / (detail_energy + approx_energy)
    denom = max(1e-6, 1.0 - threshold)
    score = max(0.0, min(1.0, (ratio - threshold) / denom))
    return {"score": score, "enabled": True, "detail_ratio": ratio, "wavelet_type": wavelet_type, "levels": levels}


def analyze_frequency(
    image,
    fft_enabled: bool = True,
    dct_enabled: bool = True,
    wavelet_enabled: bool = True,
    fft_threshold: float = 0.7,
    dct_threshold: float = 0.6,
    wavelet_threshold: float = 0.5,
    wavelet_type: str = "haar",
    wavelet_levels: int = 1,
    baseline: Optional[Dict] = None,
) -> Dict:
    gray = pil_to_gray_f(image)

    fft_res = fft_anomaly(gray, threshold=fft_threshold) if fft_enabled else {"score": 0.0, "disabled": True}
    dct_res = dct_anomaly(gray, threshold=dct_threshold) if dct_enabled else {"score": 0.0, "disabled": True}
    if wavelet_enabled:
        wavelet_res = wavelet_anomaly(gray, threshold=wavelet_threshold, wavelet_type=wavelet_type, levels=wavelet_levels)
    else:
        wavelet_res = {"score": 0.0, "enabled": False}

    # Baseline deviation adjustments (simple z-score like heuristic).
    if baseline:
        def deviation(value, mean, std):
            if std <= 0:
                return 0.0
            return abs(value - mean) / std

        fft_dev = deviation(fft_res["high_freq_ratio"], baseline.get("fft_high_freq_ratio_mean", 0.2), baseline.get("fft_high_freq_ratio_std", 0.05))
        dct_dev = deviation(dct_res["hf_lf_ratio"], baseline.get("dct_hf_lf_ratio_mean", 0.2), baseline.get("dct_hf_lf_ratio_std", 0.05))
        wavelet_ratio = wavelet_res.get("detail_ratio", 0.0)
        wave_dev = deviation(wavelet_ratio, baseline.get("wavelet_detail_ratio_mean", 0.2), baseline.get("wavelet_detail_ratio_std", 0.05))
        baseline_score = min(1.0, (fft_dev + dct_dev + wave_dev) / 3.0)
    else:
        baseline_score = 0.0

    scores = []
    if fft_enabled:
        scores.append(fft_res["score"])
    if dct_enabled:
        scores.append(dct_res["score"])
    if wavelet_enabled:
        scores.append(wavelet_res.get("score", 0.0))
    if baseline is not None:
        scores.append(baseline_score)
    score = max(0.0, min(1.0, sum(scores) / len(scores))) if scores else 0.0

    return {
        "score": score,
        "details": {
            "fft": fft_res,
            "dct": dct_res,
            "wavelet": wavelet_res,
            "baseline_score": baseline_score,
        },
    }
