# Phase 5 Test Plan (Structural Analysis)

Scope: QR/barcode detection, screenshot heuristics, synthetic text overlay detection.

Assumptions
- Python 3.11, pytest runner.
- OpenCV installed; pyzbar optional (if installed, barcode decoding tested).

Test Categories and Cases

1) QR Code Detection
- If a QR fixture is available, decoded content should be returned.
- Otherwise, schema remains consistent with `found=false`.

2) Barcode Detection
- If pyzbar is unavailable, module returns `status=unavailable`.
- If pyzbar available and barcode fixture exists, decoded content appears.

3) Screenshot Heuristics
- Plain images should not trigger screenshot detection.
- UI-like image (if fixture exists) increases confidence.

4) Synthetic Text Overlay
- Plain images should not flag synthetic text.
- Text-heavy fixture may produce overlay regions (non-deterministic).

5) Scoring Integration
- Module score normalized to [0,1].
- Module score present even if some techniques are disabled.

6) API/CLI Behavior
- `--modules structural` runs structural only and returns module details.
- Unsupported modules rejected cleanly; structural accepted.
