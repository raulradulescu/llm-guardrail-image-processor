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

**Tests:** 27 passing | **Thresholds:** SAFE <0.4, SUSPICIOUS 0.4-0.6, DANGEROUS ≥0.6

## Quick Start

```bash
source .venv/bin/activate && pytest tests/ -v
uvicorn imageguard.api:app --port 8080
curl -X POST localhost:8080/api/v1/analyze -F "image=@test.png"
curl localhost:8080/metrics
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

## Enhanced Features (Latest)

| Feature | File | Description |
|---------|------|-------------|
| Magic byte validation | `preprocess.py` | Validates image headers match file extension |
| ROT13/Leetspeak detection | `text_analysis.py` | Decodes obfuscated text patterns |
| Marked image overlays | `overlays.py` | Visual annotations on flagged regions |
| Multi-language OCR | `config.yaml` | Supports eng, fra, deu, spa |
| CI security scan | `.github/workflows/security.yml` | Safety, pip-audit, Bandit, CodeQL |
| Enhanced OCR | `text_analysis.py` | Multi-pass preprocessing, region extraction, scaling |
| Visual injection patterns | `patterns.yaml` | Detects "output X", "when asked", conditional injection |

## What's Left (Optional)

| Item | Priority | Complexity |
|------|----------|------------|
| GPU acceleration (CUDA) | Medium | Medium |

## Key Files

| File | Purpose |
|------|---------|
| `imageguard/api.py` | FastAPI + auth + rate limit + metrics |
| `imageguard/preprocess.py` | Image loading + magic byte validation |
| `imageguard/text_analysis.py` | OCR + ROT13/leetspeak detection |
| `imageguard/overlays.py` | Visual overlay annotations |
| `config.yaml` | Runtime config |
| `.github/workflows/security.yml` | CI security scanning |
| `ImageGuard_PRD_v0.2.md` | Full spec |

---
*Authors: Raul & Mark • Jan 2026*
