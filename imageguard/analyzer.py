"""ImageGuard Analyzer - Phases 1-3."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import json
from pathlib import Path
import time
import logging
import tempfile
from datetime import datetime, timezone

from .config import Config, load_config
from .preprocess import ImageValidationError, load_image, normalize_resolution
from .frequency import analyze_frequency
from .hidden_text import analyze_hidden_text
from .scoring import classify_tiered, weighted_average
from .text_analysis import analyze_text
from .patterns import load_patterns
from .steganography import analyze_steganography
from .structural import analyze_structural
from .calibration import load_calibration, platt_confidence
from .overlays import create_marked_image


CANONICAL_MODULES = {"text_extraction", "hidden_text", "frequency_analysis", "steganography", "structural"}
MODULE_ALIASES = {
    "text": "text_extraction",
    "hidden": "hidden_text",
    "frequency": "frequency_analysis",
    "stego": "steganography",
    "steganography": "steganography",
    "structural": "structural",
    "struct": "structural",
}
SUPPORTED_INPUT_MODULES = sorted(CANONICAL_MODULES | set(MODULE_ALIASES.keys()) | {"all"})

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
        if modules is None or "all" in modules:
            self.modules = [m for m, cfg in (self.config.modules or {}).items() if cfg.enabled]
        else:
            self.modules = [MODULE_ALIASES.get(m, m) for m in modules]
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
        # Load calibration data
        self.calibration = load_calibration(self.config.calibration_data)

    def _validate_modules(self, modules: List[str]) -> None:
        unknown = [m for m in modules if m not in CANONICAL_MODULES]
        if unknown:
            raise ValueError(f"Unsupported modules requested: {unknown}. Supported: {sorted(CANONICAL_MODULES)}")

    def analyze(
        self,
        image_path: str,
        return_marked: bool = False,
        include_text: Optional[bool] = None,
        max_text_length: Optional[int] = None,
    ):
        path = Path(image_path)
        file_size = path.stat().st_size if path.exists() else 0

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

        # Build image_info per PRD Section 7.3.2
        image_info = {
            "filename": path.name,
            "format": pre.original_format,
            "dimensions": {"width": pre.width, "height": pre.height},
            "size_bytes": file_size,
            "normalized_dimensions": {"width": image.width, "height": image.height},
        }

        module_scores: Dict[str, Dict] = {}
        start_overall = time.perf_counter()
        if "text_extraction" in self.modules:
            start = time.perf_counter()
            try:
                include_text = include_text if include_text is not None else (self.config.output.include_extracted_text if self.config.output else True)
                max_len = max_text_length if max_text_length is not None else (self.config.output.max_text_length if self.config.output else 10000)
                text_cfg = self.config.modules.get("text_extraction") if self.config.modules else None
                tesseract_cmd = text_cfg.tesseract_cmd if text_cfg else None
                text_result = analyze_text(
                    image,
                    pre.area,
                    languages=self.languages,
                    patterns=self.patterns,
                    include_text=include_text,
                    max_text_length=max_len,
                    tesseract_cmd=tesseract_cmd,
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
                text_result["latency_ms"] = text_result["details"]["latency_ms"]
                text_result["status"] = text_result["details"]["status"]
            module_scores["text_extraction"] = text_result

        if "hidden_text" in self.modules:
            try:
                hidden_cfg = self.config.modules.get("hidden_text") if self.config.modules else None
                thresholds = None
                if hidden_cfg:
                    thresholds = hidden_cfg.contrast_thresholds or hidden_cfg.thresholds
                edge_threshold = hidden_cfg.edge_density_threshold if hidden_cfg else 0.15
                edge_grid = hidden_cfg.edge_grid_size if hidden_cfg else 4
                # Get tesseract_cmd from text_extraction config (shared between OCR modules)
                text_cfg = self.config.modules.get("text_extraction") if self.config.modules else None
                tesseract_cmd = text_cfg.tesseract_cmd if text_cfg else None
                start = time.perf_counter()
                hidden_result = analyze_hidden_text(
                    image,
                    pre.area,
                    languages=self.languages,
                    patterns=self.patterns,
                    thresholds=thresholds,
                    edge_density_threshold=edge_threshold,
                    edge_grid_size=edge_grid,
                    tesseract_cmd=tesseract_cmd,
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
                hidden_result["latency_ms"] = hidden_result["details"]["latency_ms"]
                hidden_result["status"] = hidden_result["details"]["status"]
            module_scores["hidden_text"] = hidden_result

        if "frequency_analysis" in self.modules:
            try:
                freq_cfg = self.config.modules.get("frequency_analysis") if self.config.modules else None
                start = time.perf_counter()
                freq_result = analyze_frequency(
                    image,
                    fft_enabled=freq_cfg.fft_enabled if freq_cfg else True,
                    dct_enabled=freq_cfg.dct_enabled if freq_cfg else True,
                    wavelet_enabled=freq_cfg.wavelet_enabled if freq_cfg else True,
                    fft_threshold=freq_cfg.fft_threshold if freq_cfg else 0.7,
                    dct_threshold=freq_cfg.dct_threshold if freq_cfg else 0.6,
                    wavelet_threshold=freq_cfg.wavelet_threshold if freq_cfg else 0.5,
                    wavelet_type=freq_cfg.wavelet_type if freq_cfg else "haar",
                    wavelet_levels=freq_cfg.wavelet_levels if freq_cfg else 1,
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
                freq_result["latency_ms"] = freq_result["details"]["latency_ms"]
                freq_result["status"] = freq_result["details"]["status"]
            module_scores["frequency_analysis"] = freq_result

        if "steganography" in self.modules:
            try:
                stego_cfg = self.config.modules.get("steganography") if self.config.modules else None
                start = time.perf_counter()
                stego_result = analyze_steganography(
                    image,
                    lsb_enabled=stego_cfg.lsb_analysis if stego_cfg else True,
                    chi_square_enabled=stego_cfg.chi_square_test if stego_cfg else True,
                    rs_enabled=stego_cfg.rs_analysis if stego_cfg else True,
                    spa_enabled=stego_cfg.spa_analysis if stego_cfg else False,
                )
                elapsed = time.perf_counter() - start
            except Exception as exc:  # pragma: no cover - defensive
                if not self.config.fail_open:
                    return self._fail_closed_response(str(exc))
                stego_result = {"score": None, "details": {"status": "error", "message": str(exc)}}
                elapsed = 0
            if elapsed > self.config.timeout_seconds:
                if not self.config.fail_open:
                    return self._fail_closed_response("steganography timeout")
                stego_result = {"score": None, "details": {"status": "timeout", "message": "steganography exceeded timeout"}}
            else:
                stego_result["details"]["latency_ms"] = int(elapsed * 1000)
                stego_result["details"].setdefault("status", "ok")
                stego_result["latency_ms"] = stego_result["details"]["latency_ms"]
                stego_result["status"] = stego_result["details"]["status"]
            module_scores["steganography"] = stego_result

        if "structural" in self.modules:
            try:
                struct_cfg = self.config.modules.get("structural") if self.config.modules else None
                start = time.perf_counter()
                struct_result = analyze_structural(
                    image,
                    enable_qr=struct_cfg.detect_qr if struct_cfg else True,
                    enable_barcodes=struct_cfg.detect_barcodes if struct_cfg else True,
                    enable_screenshots=struct_cfg.detect_screenshots if struct_cfg else True,
                    analyze_decoded_content=struct_cfg.analyze_decoded_content if struct_cfg else True,
                    patterns=self.patterns,
                )
                elapsed = time.perf_counter() - start
            except Exception as exc:  # pragma: no cover - defensive
                if not self.config.fail_open:
                    return self._fail_closed_response(str(exc))
                struct_result = {"score": None, "details": {"status": "error", "message": str(exc)}}
                elapsed = 0
            if elapsed > self.config.timeout_seconds:
                if not self.config.fail_open:
                    return self._fail_closed_response("structural timeout")
                struct_result = {"score": None, "details": {"status": "timeout", "message": "structural exceeded timeout"}}
            else:
                struct_result["details"]["latency_ms"] = int(elapsed * 1000)
                struct_result["details"].setdefault("status", "ok")
                struct_result["latency_ms"] = struct_result["details"]["latency_ms"]
                struct_result["status"] = struct_result["details"]["status"]
            module_scores["structural"] = struct_result

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
            # Create marked image with visual overlays for flagged regions
            text_cfg = self.config.modules.get("text_extraction") if self.config.modules else None
            tesseract_cmd = text_cfg.tesseract_cmd if text_cfg else None
            marked_image = create_marked_image(image, module_scores, languages=self.languages, tesseract_cmd=tesseract_cmd)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                marked_image.save(tmp.name, format="PNG")
                marked_image_path = tmp.name

        # Calculate confidence based on module agreement and score distribution
        valid_scores = [m["score"] for m in module_scores.values() if m.get("score") is not None]
        if valid_scores:
            score_variance = sum((s - risk_score) ** 2 for s in valid_scores) / len(valid_scores)
            confidence_raw = max(0.5, min(0.99, 1.0 - score_variance))
        else:
            confidence_raw = 0.5

        confidence = confidence_raw
        confidence_method = "variance"
        if self.calibration:
            calibrated = platt_confidence(risk_score, self.calibration)
            if calibrated is not None:
                confidence = max(0.0, min(1.0, calibrated))
                confidence_method = "platt_scaling"

        # Build response per PRD Section 7.3.2
        return {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": processing_time_ms,
            "image_info": image_info,
            "result": {
                "classification": classification,
                "risk_score": round(risk_score, 4),
                "confidence": round(confidence, 4),
                "confidence_raw": round(confidence_raw, 4),
                "confidence_method": confidence_method,
                "threshold_used": thresholds_used.get("dangerous", 0.6) if isinstance(thresholds_used, dict) else thresholds_used,
                "thresholds": thresholds_used,
            },
            "module_scores": module_scores,
            "marked_image_path": marked_image_path,
        }

    def _fail_closed_response(self, message: str):
        """Return DANGEROUS classification when fail-closed policy is active."""
        return {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": 0,
            "image_info": None,
            "result": {
                "classification": "DANGEROUS",
                "risk_score": 1.0,
                "confidence": 1.0,
                "threshold_used": self.thresholds.dangerous,
                "thresholds": self.thresholds.__dict__,
                "note": "Fail-closed policy applied due to error",
            },
            "module_scores": {"error": {"score": 1.0, "details": {"status": "error", "message": message}}},
            "marked_image_path": None,
        }
