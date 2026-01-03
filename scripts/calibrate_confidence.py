#!/usr/bin/env python3
"""Fit Platt scaling parameters for confidence calibration.

Input JSON format:
[
  {"risk_score": 0.73, "label": 1},
  {"risk_score": 0.12, "label": 0}
]
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def fit_platt(scores: np.ndarray, labels: np.ndarray, lr: float = 0.1, epochs: int = 500) -> tuple[float, float]:
    A = 0.0
    B = 0.0
    for _ in range(epochs):
        logits = A * scores + B
        preds = 1.0 / (1.0 + np.exp(-logits))
        grad_A = np.mean((preds - labels) * scores)
        grad_B = np.mean(preds - labels)
        A -= lr * grad_A
        B -= lr * grad_B
    return float(A), float(B)


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    order = np.argsort(scores)
    sorted_labels = labels[order]
    cum_pos = np.cumsum(sorted_labels)
    cum_neg = np.cumsum(1 - sorted_labels)
    total_pos = cum_pos[-1] if len(cum_pos) else 0
    total_neg = cum_neg[-1] if len(cum_neg) else 0
    if total_pos == 0 or total_neg == 0:
        return 0.5
    auc_val = np.sum(cum_pos[sorted_labels == 0]) / (total_pos * total_neg)
    return float(auc_val)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit Platt scaling parameters")
    parser.add_argument("--input", required=True, help="Path to JSON dataset")
    parser.add_argument("--out", default="data/calibration.json", help="Output calibration file")
    parser.add_argument("--lr", type=float, default=0.1, help="Learning rate")
    parser.add_argument("--epochs", type=int, default=500, help="Training epochs")
    parser.add_argument("--safe", type=float, default=0.3, help="Safe threshold")
    parser.add_argument("--suspicious", type=float, default=0.6, help="Suspicious threshold")
    parser.add_argument("--dangerous", type=float, default=0.8, help="Dangerous threshold")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    scores = np.array([float(d["risk_score"]) for d in data], dtype=float)
    labels = np.array([int(d["label"]) for d in data], dtype=float)

    A, B = fit_platt(scores, labels, lr=args.lr, epochs=args.epochs)
    auc_val = auc(scores, labels)

    def fpr_at(thresh: float) -> float:
        preds = scores >= thresh
        fp = np.sum((preds == 1) & (labels == 0))
        tn = np.sum((preds == 0) & (labels == 0))
        return float(fp / max(fp + tn, 1))

    def fnr_at(thresh: float) -> float:
        preds = scores >= thresh
        fn = np.sum((preds == 0) & (labels == 1))
        tp = np.sum((preds == 1) & (labels == 1))
        return float(fn / max(fn + tp, 1))

    calibration = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Confidence calibration parameters for ImageGuard scoring",
        "method": "platt_scaling",
        "training_info": {
            "sample_count": int(len(scores)),
            "positive_samples": int(np.sum(labels)),
            "negative_samples": int(len(labels) - np.sum(labels)),
            "training_date": datetime.now(timezone.utc).date().isoformat(),
            "validation_auc": round(auc_val, 4),
        },
        "platt_parameters": {
            "A": round(A, 6),
            "B": round(B, 6),
            "description": "P(y=1|score) = 1 / (1 + exp(A * score + B))",
        },
        "threshold_calibration": {
            "safe": {
                "raw_threshold": args.safe,
                "calibrated_threshold": args.safe,
                "false_positive_rate": round(fpr_at(args.safe), 4),
            },
            "suspicious": {
                "raw_threshold": args.suspicious,
                "calibrated_threshold": args.suspicious,
                "false_positive_rate": round(fpr_at(args.suspicious), 4),
            },
            "dangerous": {
                "raw_threshold": args.dangerous,
                "calibrated_threshold": args.dangerous,
                "false_negative_rate": round(fnr_at(args.dangerous), 4),
            },
        },
        "per_module_calibration": {},
        "metrics": {
            "expected_calibration_error": None,
        },
    }

    Path(args.out).write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    print(f"Wrote calibration to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
