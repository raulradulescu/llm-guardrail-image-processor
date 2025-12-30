"""Configuration loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml


@dataclass
class Thresholds:
    safe: float = 0.3
    suspicious: float = 0.6
    dangerous: float = 0.8


@dataclass
class ModuleConfig:
    enabled: bool = True
    weight: float = 1.0
    languages: List[str] | None = None
    thresholds: List[int] | None = None
    wavelet_enabled: bool = True
    pattern_path: str | None = None
    baseline_model: str | None = None


@dataclass
class OutputConfig:
    include_extracted_text: bool = True
    max_text_length: int = 10000


@dataclass
class Config:
    max_image_size_mb: int = 50
    target_resolution: int = 1920
    timeout_seconds: int = 30
    thresholds: Thresholds = None  # type: ignore
    modules: Dict[str, ModuleConfig] | None = None
    fail_open: bool = True
    output: OutputConfig = None  # type: ignore

    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = Thresholds()
        if self.output is None:
            self.output = OutputConfig()


def load_config(path: str | None = None) -> Config:
    path = path or os.environ.get("IMAGEGUARD_CONFIG", "config.yaml")
    if not os.path.exists(path):
        return Config(
            modules={
                "text_extraction": ModuleConfig(enabled=True, weight=2.0, languages=["eng"]),
                "hidden_text": ModuleConfig(enabled=True, weight=1.5, thresholds=[50, 100, 150, 200, 250]),
                "frequency_analysis": ModuleConfig(enabled=True, weight=1.0, wavelet_enabled=True),
            }
        )
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    scoring = raw.get("scoring", {})
    th = scoring.get("thresholds", {})
    thresholds = Thresholds(
        safe=th.get("safe", 0.3),
        suspicious=th.get("suspicious", 0.6),
        dangerous=th.get("dangerous", 0.8),
    )

    modules_cfg: Dict[str, ModuleConfig] = {}
    modules = raw.get("modules", {})
    for name, cfg in modules.items():
        modules_cfg[name] = ModuleConfig(
            enabled=cfg.get("enabled", True),
            weight=cfg.get("weight", 1.0),
            languages=cfg.get("languages"),
            thresholds=cfg.get("thresholds"),
            wavelet_enabled=cfg.get("wavelet_enabled", True),
            pattern_path=cfg.get("pattern_path"),
            baseline_model=cfg.get("baseline_model"),
        )
    general = raw.get("general", {})
    output_cfg = raw.get("output", {})
    return Config(
        max_image_size_mb=general.get("max_image_size_mb", 50),
        target_resolution=general.get("target_resolution", 1920),
        timeout_seconds=general.get("timeout_seconds", 30),
        thresholds=thresholds,
        modules=modules_cfg,
        fail_open=general.get("fail_open", True),
        output=OutputConfig(
            include_extracted_text=output_cfg.get("include_extracted_text", True),
            max_text_length=output_cfg.get("max_text_length", 10000),
        ),
    )
