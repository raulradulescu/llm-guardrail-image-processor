# Claude Development Notes

> Context file for Claude Code sessions. Read this first.

## Project: ImageGuard

LLM-free guardrail to detect prompt injection attacks in images before they reach multimodal LLMs.

## Current State (January 2025)

| Item | Status |
|------|--------|
| PRD v0.2.1 | ✅ Complete |
| README | ✅ Complete |
| Phase 1: Text Extraction | ✅ Complete |
| Phase 2: Hidden Text | ✅ Complete |
| Phase 3: Frequency Analysis | ✅ Complete |
| Phase 4: Steganography | ✅ Complete |
| Phase 5: Structural | ✅ Complete |
| Phase 6: Optimization | ✅ Complete |

## Project Structure

```
imageguard/
├── analyzer.py      # Main orchestrator - calls all modules
├── api.py           # FastAPI REST endpoints (/analyze, /health)
├── cli.py           # CLI entry point
├── config.py        # YAML + env var config loading
├── text_analysis.py # Phase 1: Tesseract OCR + pattern matching
├── hidden_text.py   # Phase 2: Multi-threshold binarization, CLAHE
├── frequency.py     # Phase 3: FFT, DCT, Wavelet analysis
├── patterns.py      # Regex/keyword pattern matcher
├── scoring.py       # Weighted score aggregation
└── preprocess.py    # Image normalization (resize, RGB convert)
```

## Key Files

| File | Purpose |
|------|---------|
| `ImageGuard_PRD_v0.2.md` | Full PRD (4300+ lines) - Section 5 has module specs |
| `config.yaml` | Runtime config (thresholds, weights, API settings) |
| `patterns.yaml` | Injection patterns (regex + keywords) |
| `README.md` | User-facing documentation |

## Next Up: Production Hardening

- Add API auth + rate limiting
- Add metrics export (Prometheus)
- Add richer marked image overlays

## Backlog: Phase 5 (Structural)

Create `imageguard/structural.py`:
- QR/barcode detection via pyzbar
- Screenshot detection (UI element heuristics)
- **PRD Reference:** Section 5.5

## Design Decisions

1. **No LLM dependency** - Classical CV/pattern matching only
2. **Fail-open default** - Configurable to fail-closed
3. **Weighted scoring** - text(2.0), hidden(1.5), frequency(1.0)
4. **Classification tiers** - SAFE (<0.3), SUSPICIOUS (0.3-0.6), DANGEROUS (>0.6)

## Quick Commands

```bash
# Run all tests
pytest tests/ -v

# Start API server
uvicorn imageguard.api:app --reload --port 8080

# Analyze via CLI
python -m imageguard.cli analyze image.png

# Analyze via API
curl -X POST http://localhost:8080/api/v1/analyze -F "image=@test.png"
```

## PRD Quick Navigation

- **Section 5.1** - Text Extraction spec
- **Section 5.2** - Hidden Text spec
- **Section 5.3** - Frequency Analysis spec
- **Section 5.4** - Steganography spec (Phase 4)
- **Section 5.5** - Structural spec (Phase 5)
- **Section 7** - Full API specification
- **Section 9** - Data formats (patterns.yaml, config, baseline)

## Authors

Raul & Mark
