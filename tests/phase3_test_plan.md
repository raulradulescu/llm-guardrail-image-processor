# Phase 3 Test Plan (Frequency Analysis)

Scope: FFT/DCT (and optional wavelet) analysis for spectral anomalies indicating synthetic overlays, adversarial noise, or hidden signals; integration with scoring and interfaces.

Assumptions
- Python 3.11, pytest runner.
- Baseline models (frequency histograms/DCT stats) available locally with version/checksum.
- Optional wavelet analysis enabled only if within perf budget.

Test Categories and Cases

1) Baseline Loading and Validation
- Baseline file present, checksum verified; missing/invalid baseline fails health check and analyze with explicit error.
- Configured baseline path override honored via env/config.

2) FFT Analysis
- Periodic synthetic overlay fixture produces detectable high-frequency spikes and elevated anomaly score.
- Natural image fixture remains below anomaly threshold.
- Adversarial-noise fixture triggers anomaly score increase vs natural baseline.

3) DCT Analysis
- JPEG-block anomalies (edited text overlay) shift DCT coefficient distribution and raise anomaly score.
- Natural JPEG fixture stays near baseline score; no false positives above configured threshold.
- LSB-like manipulation in DCT coefficients (simulated) yields chi-square-like deviation and higher score.

4) Wavelet (if enabled)
- Wavelet detail coefficients for synthetic text overlay differ from baseline; anomaly score reflects deviation.
- Disable wavelet via config results in module skipping wavelet path and reporting it as disabled in details.

5) Scoring Integration
- Module score normalized to [0,1]; respects weight in aggregation.
- Threshold mapping: suspicious/dangerous classifications change when frequency score crosses tuned thresholds.
- If module times out or is disabled, aggregation re-normalizes weights and reports module status.

6) API/CLI Behavior
- `--modules freq` runs frequency-only and returns spectral anomaly details (peaks, energy stats).
- Unsupported modules rejected; frequency accepted.
- Health endpoint shows baseline loaded, wavelet enabled/disabled flag, and last load time.

7) Performance
- FFT/DCT processing on 1080p fixture ≤100 ms (CPU-only, documented hardware).
- Wavelet (if enabled) stays within configured budget or times out gracefully with warning and zeroed contribution.

8) Error Handling
- Non-image or corrupted input triggers validation error before frequency analysis.
- Missing baseline file surfaces clear error and sets module readiness=false.

Fixtures (to place in `tests/assets/`)
- `natural_photo.jpg`: benign baseline image.
- `synthetic_overlay.jpg`: image with added synthetic text/overlay.
- `adversarial_noise.png`: adversarially perturbed image.
- `jpeg_overlay.jpg`: text added post-JPEG to perturb DCT blocks.
- `corrupted_freq.jpg`: corrupted file for error path.

Test Harness Notes
- Deterministic scoring: fix random seeds; use fixed thresholds for tests.
- Keep baselines small and versioned; include checksum assertions.
- Mark perf tests as `slow`.
