# ImageGuard PRD (Phases 1–3 Scope)

**Version:** 0.1  
**Status:** Draft  
**Last Updated:** 17 December 2025  

## 1. Purpose and Scope
- Deliver only Phases 1–3 of ImageGuard: Preprocessing, Text Extraction & Analysis, Hidden Text Detection, and Frequency Analysis.  
- Provide API/CLI that executes these three modules; steganography and structural analysis are explicitly not implemented and must be rejected gracefully.  
- Target: fast, deterministic guardrail for image-based prompt injection signals without any LLM dependencies.

## 2. Goals and Success Criteria
- Visible and obfuscated injection detection with calibrated scoring across the three active modules.  
- End-to-end latency (CPU-only, 4 vCPU/8 GB RAM) on 1920px max-dimension images:  
  - Preprocessing ≤50 ms  
  - Text extraction ≤200 ms  
  - Hidden text ≤150 ms  
  - Frequency analysis ≤100 ms  
  - Total p95 ≤500 ms  
- Accuracy targets (measured on labeled dataset defined below):  
  - Visible text: Recall ≥95%, Precision ≥90% on injection phrases.  
  - Hidden text: Recall ≥90% on low-contrast/small-font injections with FP rate ≤5%.  
  - Frequency anomalies: Detect synthetic overlays/adversarial noise with Recall ≥80% at FP rate ≤5% on baseline corpus.  
- Robustness: corrupted/oversized/unsupported images rejected with clear errors; per-module timeouts enforced and surfaced in response.  
- Operational readiness: health check verifies OCR availability and baseline model load; metrics for latency and errors per module.

## 3. Non-Goals (for this cut)
- Steganography detection (LSB/RS/SPA) and structural analysis (QR/barcode, screenshot, synthetic overlays).  
- Video or animated GIF frame-by-frame analysis.  
- GPU acceleration.  
- Role-based auth/multi-tenancy (assume single-tenant deployment).

## 4. Functional Requirements
- Input formats: PNG, JPEG, WebP, BMP, TIFF (no animated GIF support). Max size 50 MB, max dimension 1920 px.  
- Modules: `text_extraction`, `hidden_text`, `frequency_analysis`. Requests specifying other modules return a clear “unsupported module” error.  
- Output: risk score (0.0–1.0), classification (`SAFE`/`SUSPICIOUS`/`DANGEROUS`), module scores with details, optional marked image (only for text regions).  
- Scoring: weighted average of available module scores with configurable weights; module failures/timeouts contribute a neutral score and are reported. Thresholds: safe <0.3, suspicious 0.3–0.6, dangerous ≥0.6 (tunable).  
- Internationalization: OCR languages configurable; default bundle includes English plus any specified additional packs that are installed.

## 5. System Components (Phases 1–3 Only)
- Preprocessing: format normalization to RGB numpy array, resolution standardization (longest side 1920 px), EXIF/metadata extraction.  
- Text Extraction: region detection (EAST/CRAFT or contour fallback), preprocessing (deskew, denoise, contrast normalize), Tesseract with multiple PSMs, regex/keyword matcher, n-gram heuristics.  
- Hidden Text: CLAHE + histogram equalization, multi-threshold binarization, per-channel analysis, edge-density grid scan, corner/border heuristics.  
- Frequency Analysis: FFT/DCT (wavelet optional if perf budget allows), anomaly scoring against baseline histograms; baselines versioned and loaded at startup.

## 6. Interfaces
- REST API:  
  - `POST /api/v1/analyze`: supports `modules` param limited to the three active modules; unsupported modules yield 400 with list of allowed modules.  
  - `GET /api/v1/health`: reports status, module readiness, OCR availability, baseline load state.  
- CLI: `imageguard analyze <image> [--modules text,hidden,freq] [--mark] [--threshold <float>]`. Reject unsupported module names.

## 7. Configuration Defaults
- `modules.text_extraction.enabled=true`, weight=2.0; `hidden_text.enabled=true`, weight=1.5; `frequency_analysis.enabled=true`, weight=1.0.  
- Disabled-by-default placeholders for stego/structural remain in config but must be commented out or marked “future”.  
- Timeouts: preprocessing 2000 ms, per-module 300 ms default; configurable.  
- Paths: pattern DB and frequency baselines must be provided and versioned with checksums.  
- OCR languages: `['eng']` required; extend list only if corresponding Tesseract packs are installed.

## 8. Testing and Datasets
- Datasets:  
  - Benign: natural photos, clean documents/screenshots, memes without instructions.  
  - Malicious: visible injection phrases, low-contrast/small-font injections, synthetic overlays with adversarial noise.  
  - Edge: corrupted headers, extreme aspect ratios, max-dimension images.  
- Tests:  
  - Unit: preprocessing, OCR wrapper, regex/pattern matcher, hidden-text thresholds, FFT/DCT analyzers, scoring.  
  - Integration: end-to-end API/CLI runs with module gating and config loading.  
  - Performance: latency benchmarks per module on target hardware; p95 tracked.  
  - Calibration: weight/threshold tuning script using the labeled dataset; store calibration results (date, dataset hash).

## 9. Deployment and Packaging
- Dependencies limited to Phases 1–3: Python 3.11, OpenCV, Pillow, NumPy, pytesseract, PyWavelets (if wavelet enabled), FastAPI/uvicorn.  
- Docker image includes required Tesseract language packs for configured languages and the pattern/baseline files.  
- Health check fails if OCR binary or baseline files are missing.  
- Observability: basic metrics for per-module latency, error count, timeout count; structured logs with request_id and module statuses.

## 10. Error Handling and Safety
- Reject unsupported formats, oversized images, and animated inputs with 4xx errors.  
- Per-module failures/timeouts reported in response; scoring uses only successful modules with normalization. Document fail-open vs fail-closed policy (default: fail-open with lowered confidence flag).  
- Output sanitization: extracted text truncated to 10k characters; optional redaction of decoded content if configured.

## 11. Risks and Open Questions
- Dataset availability and labeling for low-contrast injections and frequency anomalies.  
- Multilingual coverage: which additional OCR languages are mandatory for launch?  
- Acceptable fail-open vs fail-closed policy for module timeouts in production.  
- Wavelet inclusion vs latency budget—decide based on benchmarks.
