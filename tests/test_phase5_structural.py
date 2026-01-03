"""
Phase 5 contract tests: structural analysis module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ImageGuard = pytest.importorskip("imageguard", reason="imageguard package not available").ImageGuard

from .utils import make_plain_image


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
    return ImageGuard(modules=["structural"], threshold=0.5)


def test_structural_module_returns_schema(tmp_path: Path, guard: ImageGuard):
    path = make_plain_image(tmp_path)
    result = guard.analyze(str(path))
    mod = _module(result, "structural")
    assert mod is not None
    details = _field(mod, "details", {})
    assert "qr_codes" in details
    assert "barcodes" in details
    assert "screenshot_analysis" in details
    assert "text_overlay_analysis" in details
