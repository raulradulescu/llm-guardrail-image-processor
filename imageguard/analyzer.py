"""ImageGuard Analyzer for Phase 1."""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

import json
from pathlib import Path
import time
import logging
import tempfile

from .config import Config, load_config
from .preprocess import ImageValidationError, load_image, normalize_resolution
from .frequency import analyze_frequency
from .hidden_text import analyze_hidden_text
from .scoring import classify_tiered, weighted_average
from .text_analysis import analyze_text
from .patterns import load_patterns


SUPPORTED_MODULES = {"text_extraction", "hidden_text", "frequency_analysis"}

logger = logging.getLogger("imageguard")
logging.basicConfig(level=logging.INFO)


class ImageGuard:
    def __init__(
        self,
        modules: Optional[List[str]] = None,
        threshold: float | None = None,
        weights: Optional[Dict[str, float]] = None,
        languages: Optional[List[str]] = None,
        config: Optional[Config] = None,
        config_path: Optional[str] = None,
    ):
        self.config = config or load_config(config_path)
        self.modules = modules or [m for m, cfg in (self.config.modules or {}).items() if cfg.enabled]
        self.thresholds = self.config.thresholds
        self.threshold_override = threshold
        # Merge weights from config with overrides
        cfg_weights = {name: cfg.weight for name, cfg in (self.config.modules or {}).items()}
        merged_weights = cfg_weights | (weights or {})
        self.weights = merged_weights or {"text_extraction": 2.0, "hidden_text": 1.5, "frequency_analysis": 1.0}
        self.languages = languages or (self.config.modules.get("text_extraction").languages if self.config.modules else ["eng"])
        self._validate_modules(self.modules)
        # Load patterns from config if available
        pattern_path = None
        if self.config.modules and "text_extraction" in self.config.modules:
            pattern_path = getattr(self.config.modules["text_extraction"], "pattern_path", None)
        self.patterns = load_patterns(pattern_path)
        # Load frequency baseline
        self.frequency_baseline = None
        if self.config.modules and "frequency_analysis" in self.config.modules:
            baseline_path = getattr(self.config.modules["frequency_analysis"], "baseline_model", None)
            if baseline_path and Path(baseline_path).exists():
                try:
                    with open(baseline_path, "r", encoding="utf-8") as f:
                        self.frequency_baseline = json.load(f)
                except Exception:
                    self.frequency_baseline = None

    def _validate_modules(self, modules: List[str]) -> None:
        unknown = [m for m in modules if m not in SUPPORTED_MODULES]
        if unknown:
            raise ValueError(f"Unsupported modules requested: {unknown}. Supported: {sorted(SUPPORTED_MODULES)}")

    def analyze(self, image_path: str, return_marked: bool = False):
        try:
            pre = load_image(image_path, max_bytes=self.config.max_image_size_mb * 1024 * 1024)
        except FileNotFoundError:
            raise
        except ImageValidationError as exc:
            raise exc
        except Exception as exc:
            raise ImageValidationError(str(exc)) from exc

        # Basic resizing to keep OCR reliable.
        image = normalize_resolution(pre.image, max_dimension=self.config.target_resolution)

        module_scores: Dict[str, Dict] = {}
        start_overall = time.perf_counter()
        if "text_extraction" in self.modules:
            start = time.perf_counter()
            try:
                include_text = self.config.output.include_extracted_text if self.config.output else True
                max_len = self.config.output.max_text_length if self.config.output else 10000
                text_result = analyze_text(
                    image,
                    pre.area,
                    languages=self.languages,
                    patterns=self.patterns,
                    include_text=include_text,
                    max_text_length=max_len,
                )
            except Exception as exc:  # pragma: no cover - defensive
                if not self.config.fail_open:
                    return self._fail_closed_response(str(exc))
                text_result = {"score": None, "details": {"status": "error", "message": str(exc)}}
            elapsed = time.perf_counter() - start
            if elapsed > self.config.timeout_seconds:
                if not self.config.fail_open:
                    return self._fail_closed_response("text_extraction timeout")
                text_result = {"score": None, "details": {"status": "timeout", "message": "text_extraction exceeded timeout"}}
            else:
                text_result["details"]["latency_ms"] = int(elapsed * 1000)
                text_result["details"].setdefault("status", "ok")
            module_scores["text_extraction"] = text_result

        if "hidden_text" in self.modules:
            try:
                thresholds = self.config.modules.get("hidden_text").thresholds if self.config.modules and self.config.modules.get("hidden_text") else None
                start = time.perf_counter()
                hidden_result = analyze_hidden_text(
                    image,
                    pre.area,
                    languages=self.languages,
                    patterns=self.patterns,
                    thresholds=thresholds,
                )
                elapsed = time.perf_counter() - start
            except Exception as exc:  # pragma: no cover - defensive
                if not self.config.fail_open:
                    return self._fail_closed_response(str(exc))
                hidden_result = {"score": None, "details": {"status": "error", "message": str(exc)}}
                elapsed = 0
            if elapsed > self.config.timeout_seconds:
                if not self.config.fail_open:
                    return self._fail_closed_response("hidden_text timeout")
                hidden_result = {"score": None, "details": {"status": "timeout", "message": "hidden_text exceeded timeout"}}
            else:
                hidden_result["details"]["latency_ms"] = int(elapsed * 1000)
                hidden_result["details"].setdefault("status", "ok")
            module_scores["hidden_text"] = hidden_result

        if "frequency_analysis" in self.modules:
            try:
                wavelet_enabled = (
                    self.config.modules.get("frequency_analysis").wavelet_enabled
                    if self.config.modules and self.config.modules.get("frequency_analysis")
                    else True
                )
                start = time.perf_counter()
                freq_result = analyze_frequency(
                    image,
                    enable_wavelet=wavelet_enabled,
                    baseline=self.frequency_baseline,
                )
                elapsed = time.perf_counter() - start
            except Exception as exc:  # pragma: no cover - defensive
                if not self.config.fail_open:
                    return self._fail_closed_response(str(exc))
                freq_result = {"score": None, "details": {"status": "error", "message": str(exc)}}
                elapsed = 0
            if elapsed > self.config.timeout_seconds:
                if not self.config.fail_open:
                    return self._fail_closed_response("frequency_analysis timeout")
                freq_result = {"score": None, "details": {"status": "timeout", "message": "frequency_analysis exceeded timeout"}}
            else:
                freq_result["details"]["latency_ms"] = int(elapsed * 1000)
                freq_result["details"].setdefault("status", "ok")
            module_scores["frequency_analysis"] = freq_result

        scores_for_weighting = {
            name: mod_result.get("score") for name, mod_result in module_scores.items() if mod_result is not None
        }
        risk_score = weighted_average(scores_for_weighting, self.weights)
        if self.threshold_override is not None:
            classification = "DANGEROUS" if risk_score >= self.threshold_override else "SAFE"
            thresholds_used = {
                "safe": self.threshold_override,
                "suspicious": self.threshold_override,
                "dangerous": self.threshold_override,
            }
        else:
            classification = classify_tiered(
                risk_score,
                safe=self.thresholds.safe,
                suspicious=self.thresholds.suspicious,
                dangerous=self.thresholds.dangerous,
            )
            thresholds_used = self.thresholds.__dict__

        processing_time_ms = int((time.perf_counter() - start_overall) * 1000)

        marked_image_path = None
        if return_marked:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name, format="PNG")
                marked_image_path = tmp.name

        return {
            "request_id": str(uuid.uuid4()),
            "result": {
                "risk_score": risk_score,
                "classification": classification,
                "threshold_used": thresholds_used,
                "processing_time_ms": processing_time_ms,
            },
            "module_scores": module_scores,
            "marked_image_path": marked_image_path,
        }

    def _fail_closed_response(self, message: str):
        return {
            "request_id": str(uuid.uuid4()),
            "result": {
                "risk_score": 1.0,
                "classification": "DANGEROUS",
                "threshold_used": self.thresholds.__dict__,
            },
            "module_scores": {"error": {"score": 1.0, "details": {"status": "error", "message": message}}},
        }
