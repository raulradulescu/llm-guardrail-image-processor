"""Scoring and classification utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


SAFE = "SAFE"
SUSPICIOUS = "SUSPICIOUS"
DANGEROUS = "DANGEROUS"


@dataclass
class ScoreResult:
    score: float
    classification: str


def classify(risk_score: float, threshold: float = 0.6) -> str:
    # Backward compatibility single threshold
    if threshold is not None:
        return DANGEROUS if risk_score >= threshold else SAFE
    return SAFE


def classify_tiered(risk_score: float, safe: float = 0.3, suspicious: float = 0.6, dangerous: float = 0.8) -> str:
    if risk_score >= dangerous:
        return DANGEROUS
    if risk_score >= suspicious:
        return SUSPICIOUS
    if risk_score >= safe:
        return SUSPICIOUS
    return SAFE


def weighted_average(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    total_weight = 0.0
    total_score = 0.0
    for module, score in scores.items():
        weight = weights.get(module, 1.0)
        if score is None:
            continue
        total_score += weight * score
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return total_score / total_weight
