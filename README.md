# ImageGuard

Lightweight guardrail to detect prompt injection attacks hidden in images before they reach multimodal LLMs.

## Why?

Attackers embed malicious instructions in images to bypass text-based security. ImageGuard scans images using classical computer vision—no LLM required—to catch these attacks before they reach GPT-4V, Claude Vision, or Gemini.

## Features

- **Text Extraction** - OCR + pattern matching for visible injection text
- **Hidden Text Detection** - Finds low-contrast/camouflaged text
- **Frequency Analysis** - Detects spectral anomalies (FFT, DCT, Wavelet)
- **Steganography Detection** - LSB/chi-square/RS heuristics for hidden payloads
- **Structural Analysis** - QR/barcode decode + screenshot/overlay heuristics
- **REST API & CLI** - Easy integration
- **Configurable** - Thresholds, weights, fail-open/closed policies
- **Calibration + Ops** - Confidence calibration, Docker/K8s, load testing

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# System dependency (Ubuntu/Debian)
sudo apt install tesseract-ocr

# Analyze an image
python -m imageguard.cli analyze suspicious_image.png
```

## API Usage

```bash
# Start server
uvicorn imageguard.api:app --host 0.0.0.0 --port 8080

# Analyze image
curl -X POST http://localhost:8080/api/v1/analyze \
  -F "image=@image.png"
```

## Python SDK

```python
from imageguard import ImageGuard

guard = ImageGuard()
result = guard.analyze("image.png")

print(result["classification"])  # SAFE, SUSPICIOUS, or DANGEROUS
print(result["risk_score"])      # 0.0 - 1.0
```

## Classification

| Level | Score | Action |
|-------|-------|--------|
| SAFE | < 0.3 | Allow |
| SUSPICIOUS | 0.3 - 0.6 | Review |
| DANGEROUS | > 0.6 | Block |

## Configuration

Edit `config.yaml` to adjust:
- Module weights and thresholds
- OCR languages
- Fail-open/closed policy
- API settings

## Project Status

| Phase | Status |
|-------|--------|
| Text Extraction | ✅ Complete |
| Hidden Text | ✅ Complete |
| Frequency Analysis | ✅ Complete |
| Steganography | ✅ Complete |
| Structural (QR/Screenshots) | ✅ Complete |
| Integration & Optimization | ✅ Complete |

## Phase 6 Artifacts

- Calibration: `data/calibration.json` + `scripts/calibrate_confidence.py`
- Weight tuning: `scripts/calibrate_weights.py`
- Load testing: `scripts/load_test.py`
- Docker: `Dockerfile`
- Kubernetes: `k8s/deployment.yaml`, `k8s/service.yaml`
- Security review checklist: `SECURITY_REVIEW.md`

## Documentation

See [ImageGuard_PRD_v0.2.md](ImageGuard_PRD_v0.2.md) for full technical specification.

## License

Apache 2.0

## Authors

Raul & Mark
