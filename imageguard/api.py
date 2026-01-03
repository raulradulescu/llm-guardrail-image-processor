"""FastAPI server exposing ImageGuard analysis and health endpoints."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
import uuid

import yaml

import fastapi
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from .analyzer import ImageGuard, SUPPORTED_INPUT_MODULES
from .config import load_config

app = FastAPI(title="ImageGuard", version="0.1")


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
    }


@app.post("/api/v1/analyze")
@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    modules: Optional[str] = None,
    threshold: float = 0.5,
    languages: Optional[str] = None,
    return_marked: bool = False,
    include_text: Optional[bool] = None,
    max_text_length: Optional[int] = None,
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
    images: List[UploadFile] = File(...),
    modules: Optional[str] = None,
    threshold: float = 0.5,
    languages: Optional[str] = None,
):
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
            results.append(guard.analyze(str(temp_path)))
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
def get_config():
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
    }


@app.get("/api/v1/patterns")
@app.get("/patterns")
def get_patterns():
    pattern_path = None
    cfg = load_config()
    if cfg.modules and "text_extraction" in cfg.modules:
        pattern_path = cfg.modules["text_extraction"].pattern_path
    try:
        with open(pattern_path or "patterns.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {"patterns": []}
