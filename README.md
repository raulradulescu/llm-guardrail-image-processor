# ImageGuard

ImageGuard scans images for hidden prompt injection before they reach multimodal LLMs. It uses classical computer vision (no LLM required) and returns a risk score plus a SAFE/SUSPICIOUS/DANGEROUS classification.

## At a glance
- OCR and pattern matching for visible text
- Hidden text detection for low-contrast or camouflaged text
- Frequency and steganography analysis for hidden payloads
- QR/barcode decoding plus screenshot and overlay heuristics
- Obfuscation detection (ROT13, leetspeak, Unicode homoglyphs)
- Input validation (magic bytes, size, dimensions, animation)
- CLI, REST API, and Python SDK
- Configurable thresholds, weights, and fail-open/closed behavior
- Prometheus metrics, API key auth, rate limiting, CORS

## What it supports

### Inputs
- Formats: PNG, JPEG/JPG, GIF (non-animated), BMP, WebP, TIFF/TIF
- Size limit: 50 MB by default (configurable)
- Dimension limit: 3000 px per side (built-in limit)
- Normalization: EXIF-aware orientation, RGB conversion, resize to `target_resolution` (default 1920)
- Magic byte validation: extension vs content check

### Detection modules
| Module | Aliases | What it checks |
|--------|---------|----------------|
| `text_extraction` | `text` | OCR + pattern matching, ROT13, leetspeak, homoglyph normalization |
| `hidden_text` | `hidden` | Low-contrast/camouflaged text + edge density heuristics |
| `frequency_analysis` | `frequency` | FFT, DCT, Wavelet spectral checks |
| `steganography` | `stego` | LSB, chi-square, RS analysis (SPA optional) |
| `structural` | `struct` | QR/barcode decoding, screenshot and overlay heuristics |

### Outputs
- JSON with classification, risk score, confidence, image info, and per-module details
- Optional marked image overlays (PNG) when requested
- Prometheus metrics when enabled

### Interfaces
- CLI: `imageguard` or `./imageguard-cli`
- Python SDK: `ImageGuard`
- REST API:
  - `POST /api/v1/analyze` and `POST /api/v1/analyze/batch` (max 10 images)
  - `GET /api/v1/health`, `GET /api/v1/config`, `GET /api/v1/patterns`
  - `GET /api/v1/metrics` (if enabled)
- Short aliases without `/api/v1` are also available (for example, `/analyze`, `/health`).

### OCR languages
- Any installed Tesseract language pack
- Default config: `eng`, `fra`, `deu`, `spa`

## Installation

### System dependencies
- Tesseract OCR (required for `text_extraction` and `hidden_text`)
- ZBar (required for barcode decoding; QR decoding works via OpenCV)
- libgl1 (Linux only, OpenCV runtime)
- Optional: Tesseract language packs for non-English OCR

Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr libzbar0 libgl1
```

macOS (Homebrew):
```bash
brew install tesseract zbar
```

Windows:
- Install Tesseract OCR and ZBar.
- If Tesseract is not on PATH, set `modules.text_extraction.tesseract_cmd` in `config.yaml`.

### Install from source
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Docker
```bash
docker build -t imageguard .
docker run --rm -p 8080:8080 imageguard
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Quick start

```bash
imageguard suspicious_image.png --pretty
```

## CLI usage

```bash
# Basic analysis
imageguard image.png

# Pretty JSON output
imageguard image.png --pretty

# Quick classification check
imageguard image.png | jq '.result.classification'

# Specific modules only
imageguard image.png --modules text,hidden

# Marked image overlays
imageguard image.png --mark

# Alternative methods
python -m imageguard image.png
./imageguard-cli image.png
```

**CLI options:**
| Option | Description |
|--------|-------------|
| `--pretty` | Pretty-print JSON output |
| `--modules` | Comma-separated modules (text,hidden,frequency,stego,struct,structural,all) |
| `--threshold` | Risk threshold override (single cutoff) |
| `--languages` | OCR languages (comma-separated) |
| `--mark` | Save annotated image with overlays |
| `--include-text` | Include extracted text in output |
| `--no-include-text` | Exclude extracted text from output |
| `--max-text-length` | Maximum extracted text length |

## API usage

```bash
# Start server
uvicorn imageguard.api:app --host 0.0.0.0 --port 8080

# Analyze image
curl -X POST "http://localhost:8080/api/v1/analyze" \
  -F "image=@image.png"

# Analyze image with options
curl -X POST "http://localhost:8080/api/v1/analyze?modules=text,hidden&languages=eng,fra&threshold=0.6&return_marked=true" \
  -F "image=@image.png"

# Batch analyze (max 10)
curl -X POST "http://localhost:8080/api/v1/analyze/batch" \
  -F "images=@image1.png" \
  -F "images=@image2.png"

# With API key (if enabled)
curl -X POST "http://localhost:8080/api/v1/analyze" \
  -H "X-API-Key: your-api-key" \
  -F "image=@image.png"

# Health/config/patterns
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/config
curl http://localhost:8080/api/v1/patterns

# Metrics (if enabled)
curl http://localhost:8080/metrics
```

Optional query params:
- `/api/v1/analyze`: `modules`, `threshold`, `languages`, `return_marked`, `include_text`, `max_text_length`
- `/api/v1/analyze/batch`: `modules`, `threshold`, `languages`

## Python SDK

```python
from imageguard import ImageGuard

guard = ImageGuard()
result = guard.analyze("image.png")

print(result["result"]["classification"])  # SAFE, SUSPICIOUS, or DANGEROUS
print(result["result"]["risk_score"])      # 0.0 - 1.0

# Get annotated image with visual overlays
result = guard.analyze("image.png", return_marked=True)
print(result["marked_image_path"])  # Path to annotated PNG
```

## Classification

Default tiered thresholds (from `config.yaml`):

| Level | Score | Action |
|-------|-------|--------|
| SAFE | < 0.4 | Allow |
| SUSPICIOUS | 0.4 - 0.6 | Review |
| DANGEROUS | >= 0.6 | Block |

If you pass `--threshold` (CLI) or `threshold` (API), ImageGuard uses a single cutoff: `risk_score >= threshold` is DANGEROUS, otherwise SAFE.

## Configuration

Edit `config.yaml` to adjust:
- Module weights and thresholds
- OCR languages and Tesseract path
- Fail-open/closed policy
- API settings and rate limiting
- Output settings

Useful environment variables:
- `IMAGEGUARD_CONFIG` to point to a custom config file
- `IMAGEGUARD_API_KEYS` to supply API keys (comma-separated)

## Security features

### API key authentication
```yaml
# config.yaml
api:
  require_api_key: true
  api_keys: ["key1", "key2"]  # Or use IMAGEGUARD_API_KEYS env var
```

### Rate limiting
```yaml
api:
  rate_limit_enabled: true
  rate_limit_requests: 100      # requests per window
  rate_limit_window_seconds: 60
```

### Prometheus metrics
Available at `/metrics`:
- `imageguard_requests_total` - Request count by endpoint
- `imageguard_analysis_total` - Total analyses performed
- `imageguard_analysis_by_classification` - Results by classification

## Troubleshooting

- `barcodes.status = unavailable`: install ZBar (`libzbar0` on Linux, `brew install zbar` on macOS).
- OCR errors or timeouts: install Tesseract or set `modules.text_extraction.tesseract_cmd` in `config.yaml`.
- `ImportError: cv2`: ensure Python deps installed (`pip install -r requirements.txt`).

## Artifacts and docs

- Calibration: `data/calibration.json` + `scripts/calibrate_confidence.py`
- Weight tuning: `scripts/calibrate_weights.py`
- Load testing: `scripts/load_test.py`
- Security review checklist: `SECURITY_REVIEW.md`
- CI security scanning: `.github/workflows/security.yml`
- Full technical spec: [ImageGuard_PRD_v0.2.md](ImageGuard_PRD_v0.2.md)

## Test datasets

Typographic Visual Prompts Injection Dataset:

```bash
# Place dataset in data/typographic-injection/
data/
`-- typographic-injection/
    `-- [extracted dataset files]
```

## License

Apache 2.0

## Authors

Raul & Mark
