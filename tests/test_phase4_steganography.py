"""
Phase 4 contract tests: steganography detection module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ImageGuard = pytest.importorskip("imageguard", reason="imageguard package not available").ImageGuard

from .utils import make_lsb_stego_image


def _field(obj, name, default=None):
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        if "result" in obj and isinstance(obj["result"], dict) and name in obj["result"]:
            return obj["result"][name]
    return getattr(obj, name, default)


def _module(obj, module_name):
    mod_scores = _field(obj, "module_scores", {})
    if hasattr(mod_scores, "get"):
        return mod_scores.get(module_name)
    return getattr(obj, module_name, None)


@pytest.fixture
def guard():
    return ImageGuard(modules=["steganography"], threshold=0.5)


def test_steganography_module_returns_score(tmp_path: Path, guard: ImageGuard):
    path = make_lsb_stego_image(tmp_path)
    result = guard.analyze(str(path))
    mod = _module(result, "steganography")
    assert mod is not None, "steganography module result should be present"
    score = _field(mod, "score")
    assert score is None or 0.0 <= score <= 1.0
