"""Command-line interface for ImageGuard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .analyzer import ImageGuard, SUPPORTED_MODULES


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ImageGuard analyzer")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument(
        "--modules",
        default="text_extraction",
        help=f"Comma-separated modules to run (supported: {','.join(sorted(SUPPORTED_MODULES))})",
    )
    parser.add_argument("--threshold", type=float, default=0.6, help="Risk threshold for classification")
    parser.add_argument("--languages", default="eng", help="Comma-separated OCR languages (default: eng)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--mark", action="store_true", help="Return marked image (saved to temp path)")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    languages = [l.strip() for l in args.languages.split(",") if l.strip()]

    try:
        guard = ImageGuard(modules=modules, threshold=args.threshold, languages=languages)
        result = guard.analyze(args.image, return_marked=args.mark)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
