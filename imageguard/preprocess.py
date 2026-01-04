"""Image loading and preprocessing utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional

from PIL import Image, ImageOps


DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50MB
DEFAULT_MAX_DIMENSION = 3000  # reject larger (tests use 4000x4000)

# Magic bytes for supported image formats
MAGIC_BYTES = {
    "JPEG": [
        (b"\xff\xd8\xff\xe0", "JFIF"),
        (b"\xff\xd8\xff\xe1", "EXIF"),
        (b"\xff\xd8\xff\xe2", "ICC"),
        (b"\xff\xd8\xff\xdb", "JPEG"),
        (b"\xff\xd8\xff\xee", "ADOBE"),
        (b"\xff\xd8\xff", "JPEG"),  # Generic JPEG
    ],
    "PNG": [(b"\x89PNG\r\n\x1a\n", "PNG")],
    "GIF": [(b"GIF87a", "GIF87a"), (b"GIF89a", "GIF89a")],
    "BMP": [(b"BM", "BMP")],
    "WEBP": [(b"RIFF", "RIFF")],  # WEBP starts with RIFF, then WEBP at offset 8
    "TIFF": [(b"II*\x00", "TIFF-LE"), (b"MM\x00*", "TIFF-BE")],
}

# Extension to format mapping
EXTENSION_TO_FORMAT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".gif": "GIF",
    ".bmp": "BMP",
    ".webp": "WEBP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
}


class ImageValidationError(ValueError):
    """Raised when input validation fails."""


def validate_magic_bytes(path: Path, strict: bool = True) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate image file magic bytes match the file extension.

    Args:
        path: Path to the image file
        strict: If True, raise error on mismatch; if False, just return result

    Returns:
        Tuple of (is_valid, detected_format, expected_format)
    """
    ext = path.suffix.lower()
    expected_format = EXTENSION_TO_FORMAT.get(ext)

    if not expected_format:
        # Unknown extension, can't validate
        return (True, None, None)

    try:
        with open(path, "rb") as f:
            header = f.read(12)  # Read enough bytes for all magic signatures
    except Exception:
        return (False, None, expected_format)

    if len(header) < 2:
        return (False, None, expected_format)

    # Check for WEBP specifically (RIFF....WEBP)
    if expected_format == "WEBP":
        if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
            return (True, "WEBP", expected_format)
        # Check what it actually is
        detected = _detect_format_from_magic(header)
        return (False, detected, expected_format)

    # Check if magic bytes match expected format
    if expected_format in MAGIC_BYTES:
        for magic, _ in MAGIC_BYTES[expected_format]:
            if header.startswith(magic):
                return (True, expected_format, expected_format)

    # Magic bytes don't match - detect what format it actually is
    detected = _detect_format_from_magic(header)
    return (False, detected, expected_format)


def _detect_format_from_magic(header: bytes) -> Optional[str]:
    """Detect image format from magic bytes."""
    # Check WEBP first (special case)
    if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
        return "WEBP"

    for fmt, signatures in MAGIC_BYTES.items():
        if fmt == "WEBP":
            continue  # Already handled above
        for magic, _ in signatures:
            if header.startswith(magic):
                return fmt
    return None


@dataclass
class PreprocessedImage:
    image: Image.Image
    original_format: str | None
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height


def load_image(
    path: str | os.PathLike,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
    validate_magic: bool = True,
) -> PreprocessedImage:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.is_dir():
        raise ImageValidationError("Provided path is a directory, not an image")

    size = path.stat().st_size
    if size > max_bytes:
        raise ImageValidationError(f"Image size {size} exceeds max_bytes={max_bytes}")

    # Validate magic bytes before attempting to load
    if validate_magic:
        is_valid, detected, expected = validate_magic_bytes(path)
        if not is_valid and expected:
            detected_str = detected or "unknown"
            raise ImageValidationError(
                f"Magic byte mismatch: file extension suggests {expected}, "
                f"but content appears to be {detected_str}"
            )

    try:
        with Image.open(path) as img:
            img.load()
            format = img.format
            if getattr(img, "is_animated", False):
                raise ImageValidationError("Animated images are not supported")
            if img.width > max_dimension or img.height > max_dimension:
                raise ImageValidationError("Image dimensions exceed allowed maximum")
            rgb = ImageOps.exif_transpose(img.convert("RGB"))
            return PreprocessedImage(image=rgb, original_format=format, width=rgb.width, height=rgb.height)
    except ImageValidationError:
        raise
    except Exception as exc:
        raise ImageValidationError(f"Failed to load image: {exc}") from exc


def normalize_resolution(image: Image.Image, max_dimension: int = 1920) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_dimension:
        return image
    scale = max_dimension / float(max(width, height))
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, resample=Image.BILINEAR)
