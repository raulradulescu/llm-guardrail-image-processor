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
- **Obfuscation Detection** - ROT13, leetspeak, and Unicode homoglyph decoding
- **Magic Byte Validation** - Validates image headers match file extensions
- **Visual Overlays** - Annotated images highlighting flagged regions
- **Multi-language OCR** - English, French, German, Spanish support
- **REST API & CLI** - Easy integration
- **Configurable** - Thresholds, weights, fail-open/closed policies
- **Calibration + Ops** - Confidence calibration, Docker/K8s, load testing
- **CI Security Scanning** - Safety, pip-audit, Bandit, CodeQL

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# System dependency (Ubuntu/Debian)
sudo apt install tesseract-ocr

# Install ImageGuard
pip install -e .

# Analyze an image
imageguard suspicious_image.png --pretty
```

## CLI Usage

```bash
# Basic analysis
imageguard image.png

# Pretty JSON output
imageguard image.png --pretty

# Quick classification check
imageguard image.png | jq '.result.classification'

# Specific modules only
imageguard image.png --modules text,hidden

# Alternative methods
python -m imageguard image.png
./imageguard-cli image.png
```

**CLI Options:**
| Option | Description |
|--------|-------------|
| `--pretty` | Pretty-print JSON output |
| `--modules` | Comma-separated modules (text,hidden,frequency,stego,structural,all) |
| `--threshold` | Custom risk threshold |
| `--languages` | OCR languages (default: eng) |
| `--mark` | Save annotated image with overlays |
| `--include-text` | Include extracted text in output |

## API Usage

```bash
# Start server
uvicorn imageguard.api:app --host 0.0.0.0 --port 8080

# Analyze image
curl -X POST http://localhost:8080/api/v1/analyze \
  -F "image=@image.png"

# With API key (if enabled)
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "X-API-Key: your-api-key" \
  -F "image=@image.png"

# Get Prometheus metrics
curl http://localhost:8080/metrics
```

## Python SDK

```python
from imageguard import ImageGuard

guard = ImageGuard()
result = guard.analyze("image.png")

print(result["classification"])  # SAFE, SUSPICIOUS, or DANGEROUS
print(result["risk_score"])      # 0.0 - 1.0

# Get annotated image with visual overlays
result = guard.analyze("image.png", return_marked=True)
print(result["marked_image_path"])  # Path to annotated PNG

# Check for obfuscated text (ROT13, leetspeak, homoglyphs)
details = result["module_scores"]["text_extraction"]["details"]
if "obfuscation" in details:
    obf = details["obfuscation"]
    print(obf["leetspeak_decoded"])      # Decoded leetspeak
    print(obf["rot13_decoded"])          # Decoded ROT13
    print(obf["homoglyph_normalized"])   # Normalized homoglyphs
    if obf.get("homoglyph_details"):
        print(obf["homoglyph_details"]["count"])        # Number of homoglyphs
        print(obf["homoglyph_details"]["mixed_scripts"]) # True if mixed scripts
```

## Classification

| Level | Score | Action |
|-------|-------|--------|
| SAFE | < 0.4 | Allow |
| SUSPICIOUS | 0.4 - 0.6 | Review |
| DANGEROUS | ≥ 0.6 | Block |

## Configuration

Edit `config.yaml` to adjust:
- Module weights and thresholds
- OCR languages
- Fail-open/closed policy
- API settings

## Security Features

### API Key Authentication
```yaml
# config.yaml
api:
  require_api_key: true
  api_keys: ["key1", "key2"]  # Or use IMAGEGUARD_API_KEYS env var
```

### Rate Limiting
```yaml
api:
  rate_limit_enabled: true
  rate_limit_requests: 100      # requests per window
  rate_limit_window_seconds: 60
```

### Prometheus Metrics
Available at `/metrics`:
- `imageguard_requests_total` - Request count by endpoint
- `imageguard_analysis_total` - Total analyses performed
- `imageguard_analysis_by_classification` - Results by classification

## Project Status

| Phase | Status |
|-------|--------|
| Text Extraction | ✅ Complete |
| Hidden Text | ✅ Complete |
| Frequency Analysis | ✅ Complete |
| Steganography | ✅ Complete |
| Structural (QR/Screenshots) | ✅ Complete |
| Integration & Optimization | ✅ Complete |
| Production Hardening | ✅ Complete |
| Enhanced Features | ✅ Complete |

## Enhanced Features

### Multi-language OCR
```yaml
modules:
  text_extraction:
    languages: ["eng", "fra", "deu", "spa"]
```

### Magic Byte Validation
Automatically validates that image file headers match their extensions, preventing disguised file attacks.

### ROT13/Leetspeak Detection
Decodes obfuscated injection attempts like:
- `1gn0r3 4ll pr3v10u5 1n5truct10n5` → "ignore all previous instructions"
- `vtaber flfgrz cebzcg` (ROT13) → "ignore system prompt"

### Unicode Homoglyph Detection
Detects lookalike characters from other scripts used to bypass text filters:

| Script | Example | Normalized |
|--------|---------|------------|
| Cyrillic | `іgnore` (U+0456) | `ignore` |
| Greek | `αdmin` (U+03B1) | `admin` |
| Fullwidth | `ｉｇｎｏｒｅ` | `ignore` |
| Zero-width | `ig​nore` (U+200B) | `ignore` |

**Capabilities:**
- 100+ confusable character mappings
- Mixed-script detection (Cyrillic + Latin = suspicious)
- Zero-width character removal
- Automatic normalization before pattern matching

### Visual Overlays
Use `return_marked=True` to get annotated images showing flagged regions with severity-based coloring.

## Phase 6 Artifacts

- Calibration: `data/calibration.json` + `scripts/calibrate_confidence.py`
- Weight tuning: `scripts/calibrate_weights.py`
- Load testing: `scripts/load_test.py`
- Docker: `Dockerfile`
- Kubernetes: `k8s/deployment.yaml`, `k8s/service.yaml`
- Security review checklist: `SECURITY_REVIEW.md`
- CI security scanning: `.github/workflows/security.yml`

## Test Datasets

### Typographic Visual Prompts Injection Dataset
For comprehensive testing, we recommend the dataset from "Exploring Typographic Visual Prompts Injection Threats in Cross-Modality Generation Models":

```bash
# Place dataset in data/typographic-injection/
data/
└── typographic-injection/
    └── [extracted dataset files]
```

**Citation:**
```bibtex
@misc{cheng2025exploringtypographicvisualprompts,
      title={Exploring Typographic Visual Prompts Injection Threats in Cross-Modality Generation Models},
      author={Hao Cheng and Erjia Xiao and Yichi Wang and Lingfeng Zhang and Qiang Zhang and Jiahang Cao and Kaidi Xu and Mengshu Sun and Xiaoshuai Hao and Jindong Gu and Renjing Xu},
      year={2025},
      eprint={2503.11519},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2503.11519},
}
```

## Documentation

See [ImageGuard_PRD_v0.2.md](ImageGuard_PRD_v0.2.md) for full technical specification.

## License

Apache 2.0

## Authors

Raul & Mark
