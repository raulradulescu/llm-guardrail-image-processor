# ImageGuard - Claude Context

> LLM-free guardrail detecting prompt injection in images via classical CV.

## Status: All Phases Complete ✅

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Text Extraction (`text_analysis.py`) | ✅ |
| 2 | Hidden Text (`hidden_text.py`) | ✅ |
| 3 | Frequency Analysis (`frequency.py`) | ✅ |
| 4 | Steganography (`steganography.py`) | ✅ |
| 5 | Structural (`structural.py`) | ✅ |
| 6 | Optimization (`calibration.py`) | ✅ |
| - | Production Hardening | ✅ |
| - | Enhanced Features | ✅ |

**Tests:** 41 passing | **Thresholds:** SAFE <0.4, SUSPICIOUS 0.4-0.6, DANGEROUS ≥0.6

## Quick Start

```bash
# Install & test
pip install -e . && pytest tests/ -v

# CLI usage
imageguard image.png --pretty
imageguard image.png | jq '.result.classification'

# API server
uvicorn imageguard.api:app --port 8080
curl -X POST localhost:8080/api/v1/analyze -F "image=@test.png"
```

## Config Essentials

```yaml
modules:
  text_extraction:
    languages: ["eng", "fra", "deu", "spa"]  # Multi-language OCR
api:
  require_api_key: false    # Set true + IMAGEGUARD_API_KEYS env
  rate_limit_enabled: true  # 100 req/60s default
  metrics_enabled: true     # /metrics endpoint
scoring:
  thresholds: {safe: 0.4, suspicious: 0.6, dangerous: 0.6}
```

## What Was Done

| Session | Work Completed |
|---------|----------------|
| Initial | PRD v0.1 review, identified gaps |
| PRD | Completed Sections 1-3, added threat model, success criteria |
| Docs | Created CLAUDE.md, README.md |
| Phase 1-3 | Fixed `scoring.py` threshold bug (0.8→0.6), fixed `config.yaml`, added response fields to `analyzer.py` |
| Phase 4-6 | User implemented; I reviewed, fixed threshold inconsistencies in `config.py` and `calibrate_confidence.py` |
| Hardening | Added to `api.py`: API key auth (`X-API-Key`), rate limiting (sliding window), Prometheus `/metrics` |
| Docs Update | Updated PRD (7.8 metrics, 12.3-12.4 auth/rate), README (security section), AGENT_PRD_PROMPT (status), SECURITY_REVIEW |
| Final | Marked all phases ✅ in PRD architecture diagram and status tables |
| Enhanced | Added: magic byte validation, ROT13/leetspeak detection, marked image overlays, multi-lang OCR, CI security scan |
| OCR Fix | Enhanced OCR with multi-pass preprocessing, region extraction, 3x scaling for typographic injection detection |
| CLI | Added `pyproject.toml`, `imageguard` command, `python -m imageguard` support |
| Homoglyphs | Added Unicode homoglyph detection (Cyrillic, Greek, fullwidth, zero-width chars) |

## Enhanced Features (Latest)

| Feature | File | Description |
|---------|------|-------------|
| CLI tool | `cli.py`, `pyproject.toml` | `imageguard image.png --pretty` |
| Enhanced OCR | `text_analysis.py` | Multi-pass preprocessing, region extraction, 3x scaling |
| Visual injection patterns | `patterns.yaml` | Detects "output X", "when asked", conditional injection |
| Magic byte validation | `preprocess.py` | Validates image headers match file extension |
| ROT13/Leetspeak detection | `text_analysis.py` | Decodes obfuscated text patterns |
| Unicode homoglyph detection | `text_analysis.py` | Detects Cyrillic/Greek/fullwidth lookalikes |
| Marked image overlays | `overlays.py` | Visual annotations on flagged regions |
| Multi-language OCR | `config.yaml` | Supports eng, fra, deu, spa |
| CI security scan | `.github/workflows/security.yml` | Safety, pip-audit, Bandit, CodeQL |

## What's Left (Optional)

| Item | Priority | Complexity |
|------|----------|------------|
| GPU acceleration (CUDA) | Medium | Medium |

## Key Files

| File | Purpose |
|------|---------|
| `imageguard/cli.py` | CLI entry point |
| `imageguard/api.py` | FastAPI + auth + rate limit + metrics |
| `imageguard/text_analysis.py` | Enhanced OCR + ROT13/leetspeak/homoglyph detection |
| `imageguard/preprocess.py` | Image loading + magic byte validation |
| `imageguard/overlays.py` | Visual overlay annotations |
| `patterns.yaml` | Injection pattern definitions |
| `pyproject.toml` | Package config + CLI entry point |
| `config.yaml` | Runtime config |

---
*Authors: Raul & Mark • Jan 2026*
