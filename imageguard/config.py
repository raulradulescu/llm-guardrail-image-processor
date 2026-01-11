"""Configuration loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml


@dataclass
class Thresholds:
    safe: float = 0.4
    suspicious: float = 0.6
    dangerous: float = 0.6


@dataclass
class ModuleConfig:
    enabled: bool = True
    weight: float = 1.0
    languages: List[str] | None = None
    thresholds: List[int] | None = None
    contrast_thresholds: List[int] | None = None
    wavelet_enabled: bool = True
    pattern_path: str | None = None
    baseline_model: str | None = None
    tesseract_cmd: str | None = None  # Path to tesseract executable
    analyze_corners: bool = True
    analyze_borders: bool = True
    edge_density_threshold: float = 0.15
    edge_grid_size: int = 4
    fft_enabled: bool = True
    dct_enabled: bool = True
    fft_threshold: float = 0.7
    dct_threshold: float = 0.6
    wavelet_threshold: float = 0.5
    wavelet_type: str = "haar"
    wavelet_levels: int = 1
    lsb_analysis: bool = True
    chi_square_test: bool = True
    rs_analysis: bool = True
    spa_analysis: bool = False
    detect_qr: bool = True
    detect_barcodes: bool = True
    detect_screenshots: bool = True
    analyze_decoded_content: bool = True


@dataclass
class OutputConfig:
    include_extracted_text: bool = True
    max_text_length: int = 10000


@dataclass
class ApiConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    require_api_key: bool = False
    api_keys: List[str] | None = None
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    cors_origins: List[str] | None = None
    metrics_enabled: bool = True


@dataclass
class Config:
    max_image_size_mb: int = 50
    target_resolution: int = 1920
    timeout_seconds: int = 30
    thresholds: Thresholds = None  # type: ignore
    calibration_data: str | None = None
    modules: Dict[str, ModuleConfig] | None = None
    fail_open: bool = True
    output: OutputConfig = None  # type: ignore
    api: ApiConfig = None  # type: ignore

    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = Thresholds()
        if self.output is None:
            self.output = OutputConfig()
        if self.api is None:
            self.api = ApiConfig()


def load_config(path: str | None = None) -> Config:
    path = path or os.environ.get("IMAGEGUARD_CONFIG", "config.yaml")
    if not os.path.exists(path):
        return Config(
            modules={
                "text_extraction": ModuleConfig(enabled=True, weight=2.0, languages=["eng"]),
                "hidden_text": ModuleConfig(
                    enabled=True,
                    weight=1.5,
                    contrast_thresholds=[50, 100, 150, 200, 250],
                    analyze_corners=True,
                    analyze_borders=True,
                    edge_density_threshold=0.15,
                    edge_grid_size=8,
                ),
                "frequency_analysis": ModuleConfig(
                    enabled=True,
                    weight=1.0,
                    fft_enabled=True,
                    dct_enabled=True,
                    wavelet_enabled=True,
                    wavelet_threshold=0.5,
                    wavelet_type="haar",
                    wavelet_levels=2,
                ),
                "steganography": ModuleConfig(
                    enabled=True,
                    weight=1.0,
                    lsb_analysis=True,
                    chi_square_test=True,
                    rs_analysis=True,
                    spa_analysis=False,
                ),
            }
        )
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    scoring = raw.get("scoring", {})
    th = scoring.get("thresholds", {})
    thresholds = Thresholds(
        safe=th.get("safe", 0.4),
        suspicious=th.get("suspicious", 0.6),
        dangerous=th.get("dangerous", 0.6),
    )

    modules_cfg: Dict[str, ModuleConfig] = {}
    modules = raw.get("modules", {})
    for name, cfg in modules.items():
        modules_cfg[name] = ModuleConfig(
            enabled=cfg.get("enabled", True),
            weight=cfg.get("weight", 1.0),
            languages=cfg.get("languages"),
            thresholds=cfg.get("thresholds"),
            contrast_thresholds=cfg.get("contrast_thresholds"),
            wavelet_enabled=cfg.get("wavelet_enabled", True),
            pattern_path=cfg.get("pattern_path"),
            baseline_model=cfg.get("baseline_model"),
            tesseract_cmd=cfg.get("tesseract_cmd"),
            analyze_corners=cfg.get("analyze_corners", True),
            analyze_borders=cfg.get("analyze_borders", True),
            edge_density_threshold=cfg.get("edge_density_threshold", 0.15),
            edge_grid_size=cfg.get("edge_grid_size", 4),
            fft_enabled=cfg.get("fft_enabled", True),
            dct_enabled=cfg.get("dct_enabled", True),
            fft_threshold=cfg.get("fft_threshold", 0.7),
            dct_threshold=cfg.get("dct_threshold", 0.6),
            wavelet_threshold=cfg.get("wavelet_threshold", 0.5),
            wavelet_type=cfg.get("wavelet_type", "haar"),
            wavelet_levels=cfg.get("wavelet_levels", 1),
            lsb_analysis=cfg.get("lsb_analysis", True),
            chi_square_test=cfg.get("chi_square_test", True),
            rs_analysis=cfg.get("rs_analysis", True),
            spa_analysis=cfg.get("spa_analysis", False),
            detect_qr=cfg.get("detect_qr", True),
            detect_barcodes=cfg.get("detect_barcodes", True),
            detect_screenshots=cfg.get("detect_screenshots", True),
            analyze_decoded_content=cfg.get("analyze_decoded_content", True),
        )
    general = raw.get("general", {})
    output_cfg = raw.get("output", {})
    api_cfg = raw.get("api", {})

    # Load API keys from env var if not in config
    api_keys = api_cfg.get("api_keys", [])
    env_keys = os.environ.get("IMAGEGUARD_API_KEYS", "")
    if env_keys:
        api_keys = [k.strip() for k in env_keys.split(",") if k.strip()]

    return Config(
        max_image_size_mb=general.get("max_image_size_mb", 50),
        target_resolution=general.get("target_resolution", 1920),
        timeout_seconds=general.get("timeout_seconds", 30),
        thresholds=thresholds,
        calibration_data=scoring.get("calibration_data"),
        modules=modules_cfg,
        fail_open=general.get("fail_open", True),
        output=OutputConfig(
            include_extracted_text=output_cfg.get("include_extracted_text", True),
            max_text_length=output_cfg.get("max_text_length", 10000),
        ),
        api=ApiConfig(
            host=api_cfg.get("host", "0.0.0.0"),
            port=api_cfg.get("port", 8080),
            require_api_key=api_cfg.get("require_api_key", False),
            api_keys=api_keys if api_keys else None,
            rate_limit_enabled=api_cfg.get("rate_limit_enabled", True),
            rate_limit_requests=api_cfg.get("rate_limit_requests", 100),
            rate_limit_window_seconds=api_cfg.get("rate_limit_window_seconds", 60),
            cors_origins=api_cfg.get("cors_origins", ["*"]),
            metrics_enabled=api_cfg.get("metrics_enabled", True),
        ),
    )
