# Security Review Checklist (Phase 6)

## Status
- Overall: Complete
- Owner: Raul & Mark
- Date: January 2026

## Findings Summary
- Open findings: 1
- Resolved findings: 14
- Notes: Core security features implemented. Obfuscation detection (ROT13, leetspeak, homoglyphs) added.

## Checklist

### Input Handling
- [x] Validate magic bytes for image types
- [x] Enforce max file size and dimensions
- [x] Reject animated images
- [x] Enforce file count limits on batch requests (max 10)

### Output Safety
- [x] Extracted text truncation supported
- [x] Optional text suppression supported
- [x] Marked image redaction and overlays reviewed

### Service Hardening
- [x] Rate limiting enabled (configurable via `api.rate_limit_*`)
- [x] API key authentication enabled (configurable via `api.require_api_key`)
- [x] CORS policy defined (configurable via `api.cors_origins`)
- [x] Request timeouts enforced at web server

### Dependencies
- [x] Pin core dependencies in `requirements.txt`
- [x] Vulnerability scan (pip-audit, safety) in CI
- [ ] OS package updates (container) verified

### Observability
- [x] Per-module latency reporting
- [x] Centralized logging configuration
- [x] Metrics endpoint or exporter (`/metrics` Prometheus format)

### Secrets
- [x] No secrets in repo (API keys via env var `IMAGEGUARD_API_KEYS`)
- [x] Env var usage documented

## Configuration

### Enabling API Key Authentication
```yaml
# config.yaml
api:
  require_api_key: true
  api_keys: []  # Or set via IMAGEGUARD_API_KEYS env var
```

```bash
# Environment variable (comma-separated)
export IMAGEGUARD_API_KEYS="key1,key2,key3"
```

### Rate Limiting
```yaml
api:
  rate_limit_enabled: true
  rate_limit_requests: 100    # requests per window
  rate_limit_window_seconds: 60
```

### Prometheus Metrics
Access at `/metrics` or `/api/v1/metrics`. Metrics include:
- `imageguard_requests_total` - Request count by endpoint
- `imageguard_request_duration_seconds` - Request latency
- `imageguard_analysis_total` - Total analyses performed
- `imageguard_analysis_by_classification` - Results by classification
- `imageguard_requests_in_progress` - Current active requests

## Follow-up Actions
1. ~~Add API key middleware for FastAPI.~~ ✅ Done
2. ~~Add basic rate limiting.~~ ✅ Done
3. ~~Add dependency vulnerability scan to CI.~~ ✅ Done (`.github/workflows/security.yml`)
4. ~~Add magic byte validation for image uploads.~~ ✅ Done (`preprocess.py`)
5. ~~Review marked image overlay implementation.~~ ✅ Done (`overlays.py`)
6. ~~Add obfuscation detection (ROT13, leetspeak).~~ ✅ Done (`text_analysis.py`)
7. ~~Add Unicode homoglyph detection.~~ ✅ Done (`text_analysis.py`)

## Obfuscation Detection

ImageGuard detects the following text obfuscation techniques:

### ROT13 Encoding
Detects text encoded with ROT13 cipher when decoded text contains injection keywords.
- Example: `vtaber flfgrz cebzcg` → `ignore system prompt`

### Leetspeak
Decodes number/symbol substitutions for letters.
- Example: `1gn0r3 4ll 1n5truct10n5` → `ignore all instructions`

### Unicode Homoglyphs
Detects lookalike characters from other scripts:

| Type | Example | Risk |
|------|---------|------|
| Cyrillic | `іgnore` (U+0456) | High - visually identical |
| Greek | `αdmin` (U+03B1) | High - visually similar |
| Fullwidth | `ｉｇｎｏｒｅ` | Medium - spacing differs |
| Zero-width | `ig​nore` (U+200B) | High - invisible insertion |
| Mixed scripts | Cyrillic + Latin | Very High - intentional evasion |

All detected homoglyphs are normalized to ASCII before pattern matching, ensuring injection attempts using confusable characters are caught.
