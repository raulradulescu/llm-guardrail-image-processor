"""Calibration utilities for confidence scoring."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Optional


def load_calibration(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def platt_confidence(score: float, calibration: Dict[str, Any]) -> Optional[float]:
    try:
        params = calibration.get("platt_parameters", {})
        A = float(params.get("A"))
        B = float(params.get("B"))
        return 1.0 / (1.0 + math.exp(A * score + B))
    except Exception:
        return None
