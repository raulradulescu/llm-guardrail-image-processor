"""Image loading and preprocessing utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageOps


DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50MB
DEFAULT_MAX_DIMENSION = 3000  # reject larger (tests use 4000x4000)


class ImageValidationError(ValueError):
    """Raised when input validation fails."""


@dataclass
class PreprocessedImage:
    image: Image.Image
    original_format: str | None
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height


def load_image(path: str | os.PathLike, max_bytes: int = DEFAULT_MAX_BYTES, max_dimension: int = DEFAULT_MAX_DIMENSION) -> PreprocessedImage:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.is_dir():
        raise ImageValidationError("Provided path is a directory, not an image")

    size = path.stat().st_size
    if size > max_bytes:
        raise ImageValidationError(f"Image size {size} exceeds max_bytes={max_bytes}")

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
