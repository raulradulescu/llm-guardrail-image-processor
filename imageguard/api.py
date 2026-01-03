"""FastAPI server exposing ImageGuard analysis and health endpoints."""

from __future__ import annotations

import shutil
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import List, Optional
import uuid

import yaml

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from .analyzer import ImageGuard, SUPPORTED_INPUT_MODULES
from .config import load_config

# Load config at startup
_config = load_config()

app = FastAPI(title="ImageGuard", version="0.2.0")

# CORS middleware
if _config.api and _config.api.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Prometheus Metrics ---
_metrics = {
    "requests_total": defaultdict(int),
    "requests_duration_seconds": defaultdict(list),
    "requests_in_progress": 0,
    "analysis_total": 0,
    "analysis_by_classification": defaultdict(int),
}


def _format_prometheus_metrics() -> str:
    """Format metrics in Prometheus exposition format."""
    lines = []

    # Request counters by endpoint
    lines.append("# HELP imageguard_requests_total Total number of requests")
    lines.append("# TYPE imageguard_requests_total counter")
    for endpoint, count in _metrics["requests_total"].items():
        lines.append(f'imageguard_requests_total{{endpoint="{endpoint}"}} {count}')

    # Request duration histogram (simplified as summary)
    lines.append("# HELP imageguard_request_duration_seconds Request duration in seconds")
    lines.append("# TYPE imageguard_request_duration_seconds summary")
    for endpoint, durations in _metrics["requests_duration_seconds"].items():
        if durations:
            avg = sum(durations[-100:]) / len(durations[-100:])  # Last 100 requests
            lines.append(f'imageguard_request_duration_seconds_sum{{endpoint="{endpoint}"}} {sum(durations[-100:]):.4f}')
            lines.append(f'imageguard_request_duration_seconds_count{{endpoint="{endpoint}"}} {len(durations[-100:])}')

    # Analysis counters
    lines.append("# HELP imageguard_analysis_total Total number of image analyses")
    lines.append("# TYPE imageguard_analysis_total counter")
    lines.append(f"imageguard_analysis_total {_metrics['analysis_total']}")

    lines.append("# HELP imageguard_analysis_by_classification Analysis results by classification")
    lines.append("# TYPE imageguard_analysis_by_classification counter")
    for classification, count in _metrics["analysis_by_classification"].items():
        lines.append(f'imageguard_analysis_by_classification{{classification="{classification}"}} {count}')

    # Requests in progress gauge
    lines.append("# HELP imageguard_requests_in_progress Current number of requests being processed")
    lines.append("# TYPE imageguard_requests_in_progress gauge")
    lines.append(f"imageguard_requests_in_progress {_metrics['requests_in_progress']}")

    return "\n".join(lines) + "\n"


# --- Rate Limiting ---
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit. Returns True if allowed."""
    if not _config.api or not _config.api.rate_limit_enabled:
        return True

    now = time.time()
    window = _config.api.rate_limit_window_seconds
    max_requests = _config.api.rate_limit_requests

    # Clean old entries
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if now - ts < window
    ]

    if len(_rate_limit_store[client_ip]) >= max_requests:
        return False

    _rate_limit_store[client_ip].append(now)
    return True


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --- API Key Authentication ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)):
    """Verify API key if authentication is required."""
    if not _config.api or not _config.api.require_api_key:
        return None

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    valid_keys = _config.api.api_keys or []
    if api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key


# --- Middleware for metrics and rate limiting ---
@app.middleware("http")
async def metrics_and_rate_limit_middleware(request: Request, call_next):
    """Middleware for metrics collection and rate limiting."""
    client_ip = get_client_ip(request)
    endpoint = request.url.path

    # Skip rate limiting for health and metrics endpoints
    skip_rate_limit = endpoint in ["/health", "/api/v1/health", "/metrics", "/api/v1/metrics"]

    if not skip_rate_limit and not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "retry_after_seconds": _config.api.rate_limit_window_seconds}
        )

    # Track metrics
    _metrics["requests_total"][endpoint] += 1
    _metrics["requests_in_progress"] += 1
    start_time = time.time()

    try:
        response = await call_next(request)
        return response
    finally:
        duration = time.time() - start_time
        _metrics["requests_duration_seconds"][endpoint].append(duration)
        _metrics["requests_in_progress"] -= 1


def check_tesseract() -> bool:
    import subprocess

    try:
        subprocess.run(["tesseract", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return True
    except Exception:
        return False


@app.get("/api/v1/health")
@app.get("/health")
def health():
    cfg = load_config()
    pattern_path = cfg.modules.get("text_extraction").pattern_path if cfg.modules and cfg.modules.get("text_extraction") else None
    freq_baseline = cfg.modules.get("frequency_analysis").baseline_model if cfg.modules and cfg.modules.get("frequency_analysis") else None
    return {
        "status": "healthy" if check_tesseract() else "degraded",
        "version": app.version,
        "modules_loaded": SUPPORTED_INPUT_MODULES,
        "tesseract": check_tesseract(),
        "pattern_db": Path(pattern_path).exists() if pattern_path else False,
        "frequency_baseline": Path(freq_baseline).exists() if freq_baseline else False,
        "rate_limiting": cfg.api.rate_limit_enabled if cfg.api else False,
        "api_key_required": cfg.api.require_api_key if cfg.api else False,
    }


@app.get("/api/v1/metrics")
@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    if not _config.api or not _config.api.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    return PlainTextResponse(_format_prometheus_metrics(), media_type="text/plain")


@app.post("/api/v1/analyze")
@app.post("/analyze")
async def analyze(
    request: Request,
    image: UploadFile = File(...),
    modules: Optional[str] = None,
    threshold: float = 0.5,
    languages: Optional[str] = None,
    return_marked: bool = False,
    include_text: Optional[bool] = None,
    max_text_length: Optional[int] = None,
    _api_key: str = Depends(verify_api_key),
):
    requested_modules: List[str] = [m for m in (modules or "all").split(",") if m]
    languages_list: List[str] = [l for l in (languages or "eng").split(",") if l]

    try:
        guard = ImageGuard(modules=requested_modules, threshold=threshold, languages=languages_list)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    # Write upload to temp file for PIL/OpenCV compatibility.
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix or ".img") as tmp:
        temp_path = Path(tmp.name)
        await image.seek(0)
        shutil.copyfileobj(image.file, tmp)

    try:
        result = guard.analyze(
            str(temp_path),
            return_marked=return_marked,
            include_text=include_text,
            max_text_length=max_text_length,
        )

        # Update metrics
        _metrics["analysis_total"] += 1
        classification = result.get("result", {}).get("classification", "UNKNOWN")
        _metrics["analysis_by_classification"][classification] += 1

    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return result


@app.post("/api/v1/analyze/batch")
@app.post("/analyze/batch")
async def analyze_batch(
    request: Request,
    images: List[UploadFile] = File(...),
    modules: Optional[str] = None,
    threshold: float = 0.5,
    languages: Optional[str] = None,
    _api_key: str = Depends(verify_api_key),
):
    # Check batch size limit
    max_batch = 10
    if len(images) > max_batch:
        return JSONResponse(
            {"error": f"Batch size exceeds limit of {max_batch} images"},
            status_code=400
        )

    requested_modules: List[str] = [m for m in (modules or "all").split(",") if m]
    languages_list: List[str] = [l for l in (languages or "eng").split(",") if l]
    guard = ImageGuard(modules=requested_modules, threshold=threshold, languages=languages_list)

    results = []
    for image in images:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix or ".img") as tmp:
            temp_path = Path(tmp.name)
            await image.seek(0)
            shutil.copyfileobj(image.file, tmp)
        try:
            result = guard.analyze(str(temp_path))
            results.append(result)

            # Update metrics
            _metrics["analysis_total"] += 1
            classification = result.get("result", {}).get("classification", "UNKNOWN")
            _metrics["analysis_by_classification"][classification] += 1

        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    summary = {
        "safe": sum(1 for r in results if r.get("result", {}).get("classification") == "SAFE"),
        "suspicious": sum(1 for r in results if r.get("result", {}).get("classification") == "SUSPICIOUS"),
        "dangerous": sum(1 for r in results if r.get("result", {}).get("classification") == "DANGEROUS"),
        "average_processing_time_ms": int(sum(r.get("processing_time_ms", 0) for r in results) / max(len(results), 1)),
    }
    return {"batch_id": str(uuid.uuid4()), "total_images": len(results), "results": results, "summary": summary}


@app.get("/api/v1/config")
@app.get("/config")
def get_config(_api_key: str = Depends(verify_api_key)):
    cfg = load_config()
    return {
        "general": {
            "max_image_size_mb": cfg.max_image_size_mb,
            "timeout_seconds": cfg.timeout_seconds,
            "target_resolution": cfg.target_resolution,
            "fail_open": cfg.fail_open,
        },
        "modules": {k: v.__dict__ for k, v in (cfg.modules or {}).items()},
        "scoring": {"thresholds": cfg.thresholds.__dict__},
        "output": cfg.output.__dict__ if cfg.output else {},
        "api": {
            "rate_limit_enabled": cfg.api.rate_limit_enabled if cfg.api else False,
            "rate_limit_requests": cfg.api.rate_limit_requests if cfg.api else 100,
            "rate_limit_window_seconds": cfg.api.rate_limit_window_seconds if cfg.api else 60,
            "api_key_required": cfg.api.require_api_key if cfg.api else False,
            "metrics_enabled": cfg.api.metrics_enabled if cfg.api else True,
        },
    }


@app.get("/api/v1/patterns")
@app.get("/patterns")
def get_patterns(_api_key: str = Depends(verify_api_key)):
    pattern_path = None
    cfg = load_config()
    if cfg.modules and "text_extraction" in cfg.modules:
        pattern_path = cfg.modules["text_extraction"].pattern_path
    try:
        with open(pattern_path or "patterns.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {"patterns": []}
