# Phase 4 Test Plan (Steganography Detection)

Scope: LSB analysis, chi-square test, RS analysis, and SPA analysis (if enabled).

Assumptions
- Python 3.11, pytest runner.
- NumPy installed; Pillow used for image synthesis.
- Fixtures under `tests/assets/` or generated via `tests/utils.py`.

Test Categories and Cases

1) LSB Analysis
- Randomness score in [0,1] for synthetic images.
- Pattern detection triggers for fully uniform LSB planes (all 0 or all 1).

2) Chi-Square Test
- Returns p_value in [0,1] with is_significant boolean.
- Low p_value for synthetic LSB pair manipulation (if fixture available).

3) RS Analysis
- Returns rs_ratio in [-1,1]; embedding_detected toggles when rs_ratio near 0.

4) SPA Analysis
- estimated_embedding_rate in [0,1] for adjacent LSB pair analysis.
- Higher estimated rate on artificially randomized LSB planes.

5) Scoring Integration
- Module score normalized to [0,1].
- Module score present even when some techniques are disabled.

6) API/CLI Behavior
- `--modules steganography` runs stego only and returns module details.
- Unsupported modules rejected cleanly; steganography accepted.

Fixtures
- `stego_lsb.png`: image with embedded bits in LSBs.
- `clean.png`: benign image without embedded data.

Test Harness Notes
- Keep assertions tolerant; stego heuristics are not deterministic across all images.
