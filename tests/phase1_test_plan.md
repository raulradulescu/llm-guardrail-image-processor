# Phase 1 Test Plan

Scope: Preprocessing, OCR integration, pattern matching, scoring, and CLI/API wiring for Phases 1–3 PRD (preprocessing + text extraction/analysis only).

Assumptions
- Language: Python 3.11, pytest as the test runner.
- Images stored in `tests/assets/` with small fixtures to keep repo light.
- OCR engine: Tesseract installed with at least English (`eng`) data.
- Config paths resolved relative to project root unless overridden via env vars.

Test Categories and Cases

1) Preprocessing
- Format normalization converts PNG/JPEG/WebP/BMP/TIFF to RGB numpy arrays; rejects unsupported/animated GIFs.
- Resolution standardization scales longest side to 1920 px while preserving aspect ratio; verifies no upscaling beyond original.
- Metadata extraction returns EXIF where present; handles missing EXIF gracefully.
- Corrupted headers/images raise a clear, typed error.
- Max size enforcement: files >50 MB or oversized dimensions return validation error.

2) OCR Integration
- Runs Tesseract on clean text fixture (black text on white) and matches expected string with confidence above threshold.
- Multi-PSM fallback: when PSM 6 fails, PSM 11 recovers small text; ensure retry logic triggers.
- Language selection: when `languages=['eng']` only, disallows other codes; when multiple installed, uses provided list.
- Deskew/denoise/contrast pipeline improves OCR on skewed/noisy fixtures compared to raw OCR (assert higher confidence/character match).

3) Pattern Matching
- Regex patterns match known injection phrases (ignore previous instructions, role manipulation, jailbreak keywords) and do not fire on benign near-misses.
- Encoded-content detection: base64 regex triggers on long encoded strings but not on short random-looking tokens.
- Keyword severity weighting applied correctly per pattern id and aggregated without exceeding 1.0.

4) Scoring
- `calculate_text_score` normalizes to [0,1]; density factor applied only when text area proportion exceeds threshold.
- Imperative/structure detection adds bonus; absence keeps base score unchanged.
- Combined score uses configured weights and ignores disabled modules gracefully (for Phase 1 only text module is active).
- Threshold mapping to SAFE/SUSPICIOUS/DANGEROUS matches config.

5) CLI/API Behavior
- CLI `imageguard analyze <image>` returns JSON with module scores; missing file yields helpful error and non-zero exit.
- `--modules` rejects unsupported modules (stego/structural) with 400/explicit message; accepts `text` or `text,hidden,freq` for future.
- `--threshold` overrides config and affects classification.
- Health endpoint returns `healthy` only when OCR binary is reachable and pattern DB loaded; reports module readiness flags.

6) Performance (lightweight, deterministic checks)
- Per-module latency measured on small fixtures stays under budgets: preprocessing ≤50 ms, OCR ≤200 ms.
- End-to-end run on 1080p fixture under 500 ms on test hardware (document hardware specs in test output).

7) Error Handling
- Corrupted image triggers `InvalidImageError` (or equivalent) and 4xx in API.
- Oversized image triggers validation error before processing.
- Missing OCR binary or language pack fails health check and analyze endpoint with explicit message.

Fixtures (to place in `tests/assets/`)
- `clean_text.png`: simple phrase containing injection string.
- `benign_doc.png`: benign text without triggers.
- `low_contrast_text.png`: white-on-light-gray injection phrase.
- `skewed_text.png`: skewed injection phrase for deskew test.
- `noise_text.png`: noisy background with injection phrase.
- `base64_block.png`: image with long base64 string.
- `corrupted.jpg`: truncated/corrupted file.
- `large_image.jpg`: >50 MB or >1920 px dimension for size enforcement.

Test Harness Notes
- Use pytest markers `slow` for latency checks; gate them to run optionally in CI.
- Seed random operations; avoid network calls. Keep OCR comparisons tolerant (strip whitespace, lower-case).
- Provide helper to load assets and clean temp directories.
