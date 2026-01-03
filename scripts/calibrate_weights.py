#!/usr/bin/env python3
"""Grid-search module weights and threshold using labeled module scores.

Input JSON format:
[
  {
    "label": 1,
    "module_scores": {
      "text_extraction": 0.8,
      "hidden_text": 0.2,
      "frequency_analysis": 0.1,
      "steganography": 0.0,
      "structural": 0.1
    }
  }
]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def weighted_average(scores: dict, weights: dict) -> float:
    total_weight = 0.0
    total_score = 0.0
    for k, v in scores.items():
        if v is None:
            continue
        w = weights.get(k, 1.0)
        total_weight += w
        total_score += w * float(v)
    return total_score / total_weight if total_weight else 0.0


def f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evaluate(data, weights, threshold):
    tp = fp = tn = fn = 0
    for item in data:
        score = weighted_average(item["module_scores"], weights)
        pred = 1 if score >= threshold else 0
        label = int(item["label"])
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 0:
            tn += 1
        elif pred == 0 and label == 1:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate module weights")
    parser.add_argument("--input", required=True, help="Path to JSON dataset")
    parser.add_argument("--out", default="data/weight_calibration.json", help="Output JSON path")
    parser.add_argument("--modules", default="text_extraction,hidden_text,frequency_analysis,steganography,structural")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    weight_grid = [0.5, 1.0, 1.5, 2.0]
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]

    best = {"f1": -1}
    for w_text in weight_grid:
        for w_hidden in weight_grid:
            for w_freq in weight_grid:
                for w_stego in weight_grid:
                    for w_struct in weight_grid:
                        weights = {
                            modules[0]: w_text,
                            modules[1]: w_hidden,
                            modules[2]: w_freq,
                            modules[3]: w_stego,
                            modules[4]: w_struct,
                        }
                        for threshold in thresholds:
                            metrics = evaluate(data, weights, threshold)
                            if metrics["f1"] > best["f1"]:
                                best = {
                                    "weights": weights,
                                    "threshold": threshold,
                                    "precision": metrics["precision"],
                                    "recall": metrics["recall"],
                                    "f1": metrics["f1"],
                                }

    Path(args.out).write_text(json.dumps(best, indent=2), encoding="utf-8")
    print(f"Wrote weight calibration to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
