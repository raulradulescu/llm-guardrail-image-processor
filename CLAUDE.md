# Claude Development Notes

> Context file for Claude Code sessions. Read this first.

## Project: ImageGuard

LLM-free guardrail to detect prompt injection attacks in images before they reach multimodal LLMs.

## Current State (January 2026)

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
├── analyzer.py       # Main orchestrator - calls all modules
├── api.py            # FastAPI REST endpoints (/analyze, /health)
├── cli.py            # CLI entry point
├── config.py         # YAML + env var config loading
├── text_analysis.py  # Phase 1: Tesseract OCR + pattern matching
├── hidden_text.py    # Phase 2: Multi-threshold binarization, CLAHE
├── frequency.py      # Phase 3: FFT, DCT, Wavelet analysis
├── steganography.py  # Phase 4: LSB, chi-square, RS analysis
├── structural.py     # Phase 5: QR/barcode, screenshot detection
├── calibration.py    # Phase 6: Platt scaling confidence calibration
├── patterns.py       # Regex/keyword pattern matcher
├── scoring.py        # Weighted score aggregation
└── preprocess.py     # Image normalization (resize, RGB convert)

scripts/
├── calibrate_confidence.py  # Fit Platt scaling parameters
├── calibrate_weights.py     # Tune module weights
└── load_test.py             # Performance load testing

k8s/
├── deployment.yaml   # Kubernetes deployment spec
└── service.yaml      # Kubernetes service spec
```

## Key Files

| File | Purpose |
|------|---------|
| `ImageGuard_PRD_v0.2.md` | Full PRD (4300+ lines) - Section 5 has module specs |
| `config.yaml` | Runtime config (thresholds, weights, API settings) |
| `patterns.yaml` | Injection patterns (regex + keywords) |
| `README.md` | User-facing documentation |
| `Dockerfile` | Container build for deployment |
| `SECURITY_REVIEW.md` | Security checklist with open/resolved items |
| `data/calibration.json` | Platt scaling parameters for confidence |
| `data/frequency_baseline.json` | Baseline model for frequency analysis |

## Phase 6 Artifacts

- **Calibration**: `data/calibration.json` + `scripts/calibrate_confidence.py`
- **Weight tuning**: `scripts/calibrate_weights.py`
- **Load testing**: `scripts/load_test.py`
- **Docker**: `Dockerfile`
- **Kubernetes**: `k8s/deployment.yaml`, `k8s/service.yaml`
- **Security review**: `SECURITY_REVIEW.md`

## Production Hardening (Complete)

- [x] API key authentication (`X-API-Key` header, configurable)
- [x] Rate limiting (sliding window, configurable)
- [x] Prometheus metrics endpoint (`/metrics`)
- [x] CORS middleware (configurable origins)
- [x] Batch size limits (max 10 images)
- [ ] Magic byte validation (recommended)
- [ ] Marked image overlays (recommended)

## Design Decisions

1. **No LLM dependency** - Classical CV/pattern matching only
2. **Fail-open default** - Configurable to fail-closed
3. **Weighted scoring** - text(2.0), hidden(1.5), structural(1.2), frequency(1.0), stego(1.0)
4. **Classification tiers** - SAFE (<0.3), SUSPICIOUS (0.3-0.6), DANGEROUS (>0.6)

## Quick Commands

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Start API server
uvicorn imageguard.api:app --reload --port 8080

# Analyze via CLI
python -m imageguard.cli analyze image.png

# Analyze via API
curl -X POST http://localhost:8080/api/v1/analyze -F "image=@test.png"

# With API key (if enabled)
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "X-API-Key: your-api-key" \
  -F "image=@test.png"

# Get Prometheus metrics
curl http://localhost:8080/metrics

# Build Docker image
docker build -t imageguard:latest .

# Run with API keys
docker run -p 8080:8080 \
  -e IMAGEGUARD_API_KEYS="key1,key2" \
  imageguard:latest

# Run calibration script
python scripts/calibrate_confidence.py --input data/training.json --out data/calibration.json
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
