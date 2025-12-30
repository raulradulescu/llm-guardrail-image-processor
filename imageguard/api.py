"""FastAPI server exposing ImageGuard analysis and health endpoints."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

import fastapi
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from .analyzer import ImageGuard, SUPPORTED_MODULES
from .config import load_config
from pathlib import Path

app = FastAPI(title="ImageGuard", version="0.1")


def check_tesseract() -> bool:
    import subprocess

    try:
        subprocess.run(["tesseract", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return True
    except Exception:
        return False


@app.get("/api/v1/health")
def health():
    cfg = load_config()
    pattern_path = cfg.modules.get("text_extraction").__dict__.get("pattern_path") if cfg.modules and cfg.modules.get("text_extraction") else None
    freq_baseline = cfg.modules.get("frequency_analysis").__dict__.get("baseline_model") if cfg.modules and cfg.modules.get("frequency_analysis") else None
    return {
        "status": "healthy" if check_tesseract() else "degraded",
        "version": app.version,
        "modules_loaded": sorted(SUPPORTED_MODULES),
        "tesseract": check_tesseract(),
        "pattern_db": Path(pattern_path).exists() if pattern_path else False,
        "frequency_baseline": Path(freq_baseline).exists() if freq_baseline else False,
    }


@app.post("/api/v1/analyze")
async def analyze(
    image: UploadFile = File(...),
    modules: Optional[str] = None,
    threshold: float = 0.6,
    languages: Optional[str] = None,
    return_marked: bool = False,
):
    requested_modules: List[str] = [m for m in (modules or "text_extraction").split(",") if m]
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
        result = guard.analyze(str(temp_path), return_marked=return_marked)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return result
