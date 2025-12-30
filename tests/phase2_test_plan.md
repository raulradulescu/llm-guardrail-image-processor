# Phase 2 Test Plan (Hidden Text Detection)

Scope: Hidden/obfuscated text detection pipeline (contrast enhancement, multi-threshold binarization, per-channel analysis, edge-density heuristics) plus integration with scoring and interfaces.

Assumptions
- Python 3.11, pytest runner.
- OCR engine: Tesseract with `eng` installed.
- Fixtures under `tests/assets/`.

Test Categories and Cases

1) Contrast/Binarization Pipeline
- CLAHE + histogram equalization improves OCR recall on low-contrast fixtures vs baseline OCR (assert more matched tokens).
- Multiple thresholds produce aggregated OCR that recovers text missed in single-threshold runs.
- Adaptive threshold fallback engages when global thresholds underperform (fixture-driven check).

2) Per-Channel Analysis
- Hidden text present in a single channel (e.g., red-only) is recovered when channels are processed independently.
- No false positives on uniform single-channel images (noise-only fixture).

3) Edge-Based Heuristics
- Edge-density grid detects small high-frequency text regions even when OCR confidence is low; regions flagged in module details.
- Benign textured backgrounds do not trigger excessive flags (false positive control).

4) Region Prioritization
- Corner/border emphasis: text in corners/borders is detected/flagged; center-only benign images do not falsely trigger corner heuristics.
- Background-color-matched text (within ±5 RGB) is surfaced by multi-threshold and reported as hidden text.

5) Scoring Integration
- Hidden-text module contributes score only when new text is found vs baseline OCR; otherwise minimal/neutral contribution.
- Module score normalization to [0,1]; severity bump when hidden text contains injection patterns.
- Weight application respects config; disabled module is skipped without affecting total weight normalization.

6) API/CLI Behavior
- `--modules hidden` runs only hidden-text pipeline and returns details (thresholds tried, regions flagged, extracted text deltas).
- Requests with unsupported modules still rejected cleanly; hidden module name accepted.
- Health check reports hidden-text readiness even if OCR present but hidden pipeline disabled (status shows disabled).

7) Performance
- Pipeline latency on 1080p low-contrast fixture ≤150 ms (CPU-only, documented hardware).
- Threshold sweep count configurable; exceeding count triggers warning but still completes under budget.

8) Error Handling
- Corrupted/unsupported images rejected before hidden-text processing.
- Missing OCR binary causes hidden-text module to surface a clear error and set readiness=false.

Fixtures (to place in `tests/assets/`)
- `low_contrast_text.png`: white/gray injection phrase.
- `single_channel_red.png`: red-channel-only text on black.
- `text_in_corner.png`: small text in bottom-right corner.
- `background_match_text.png`: text color close to background.
- `textured_background.png`: textured benign background with no text.
- `corrupted_hidden.jpg`: corrupted file for error path.

Test Harness Notes
- Use tolerance for OCR text matching (case-fold, strip whitespace).
- Mark latency checks as `slow`.
- Capture per-threshold OCR results in module details for assertions.
