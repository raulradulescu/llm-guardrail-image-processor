"""Command-line interface for ImageGuard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

import numpy as np

from .analyzer import ImageGuard


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ImageGuard analyzer - Detect prompt injection attacks hidden in images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available modules:
  text, text_extraction    OCR + pattern matching for visible injection text
  hidden, hidden_text      Detect low-contrast/camouflaged text
  frequency, frequency_analysis
                           Spectral anomaly detection (FFT, DCT, Wavelet)
  stego, steganography     LSB/chi-square/RS heuristics for hidden payloads
  struct, structural       QR/barcode decode + screenshot/overlay detection
  all                      Run all modules (default)

Examples:
  imageguard image.png --pretty
  imageguard image.png --modules text,hidden
  imageguard image.png --mark --include-text
""",
    )
    parser.add_argument("image", help="Path to image file")
    parser.add_argument(
        "--modules",
        default="all",
        help="Comma-separated modules to run (default: all). See available modules below.",
    )
    parser.add_argument("--threshold", type=float, default=0.5, help="Risk threshold for classification")
    parser.add_argument("--languages", default="eng", help="Comma-separated OCR languages (default: eng)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--mark", action="store_true", help="Return marked image (saved to temp path)")
    parser.add_argument("--include-text", dest="include_text", action="store_true", help="Include extracted text")
    parser.add_argument("--no-include-text", dest="include_text", action="store_false", help="Exclude extracted text")
    parser.add_argument("--max-text-length", type=int, default=None, help="Maximum extracted text length")
    parser.set_defaults(include_text=None)
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    languages = [l.strip() for l in args.languages.split(",") if l.strip()]

    try:
        guard = ImageGuard(modules=modules, threshold=args.threshold, languages=languages)
        result = guard.analyze(
            args.image,
            return_marked=args.mark,
            include_text=args.include_text,
            max_text_length=args.max_text_length,
        )
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if args.pretty:
        print(json.dumps(result, indent=2, cls=NumpyEncoder))
    else:
        print(json.dumps(result, cls=NumpyEncoder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
