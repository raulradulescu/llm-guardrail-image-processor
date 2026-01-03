"""
Test utilities for generating image fixtures on the fly.
"""

from __future__ import annotations

import random
import uuid
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def _get_font(size: int = 32) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def make_text_image(
    tmp_path: Path,
    text: str,
    size: Tuple[int, int] = (800, 600),
    fg: Tuple[int, int, int] = (0, 0, 0),
    bg: Tuple[int, int, int] = (255, 255, 255),
    font_size: int = 32,
    filename: str | None = None,
) -> Path:
    """Create an RGB image with centered text and return the path."""
    image = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(image)
    font = _get_font(font_size)
    # textsize deprecated; use textbbox for compatibility with newer Pillow.
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    draw.text(position, text, fill=fg, font=font)
    name = filename or f"{uuid.uuid4().hex}.png"
    path = tmp_path / name
    image.save(path)
    return path


def make_low_contrast_image(tmp_path: Path, text: str) -> Path:
    """Image with low-contrast text for hidden-text tests."""
    fg = (230, 230, 230)
    bg = (245, 245, 245)
    return make_text_image(tmp_path, text, fg=fg, bg=bg, font_size=32)


def make_single_channel_image(tmp_path: Path, text: str, channel: str = "r") -> Path:
    """Create text visible only in a single channel."""
    fg_map = {
        "r": (255, 0, 0),
        "g": (0, 255, 0),
        "b": (0, 0, 255),
    }
    fg = fg_map.get(channel.lower(), (255, 0, 0))
    bg = (0, 0, 0)
    return make_text_image(tmp_path, text, fg=fg, bg=bg, font_size=32)


def make_large_image(tmp_path: Path, size: Tuple[int, int] = (4000, 4000)) -> Path:
    """Create a large blank image to test dimension/size limits."""
    image = Image.new("RGB", size, color=(255, 255, 255))
    path = tmp_path / f"large-{size[0]}x{size[1]}.png"
    image.save(path)
    return path


def write_corrupted_file(tmp_path: Path) -> Path:
    """Write a corrupted image-like file."""
    path = tmp_path / "corrupted.jpg"
    with open(path, "wb") as f:
        f.write(random.randbytes(64) if hasattr(random, "randbytes") else bytes(random.getrandbits(8) for _ in range(64)))
    return path


def make_lsb_stego_image(tmp_path: Path, message: str = "secret", size: Tuple[int, int] = (256, 256)) -> Path:
    """Create an image with a message embedded in LSBs."""
    import numpy as np

    base = Image.new("L", size, color=128)
    arr = np.array(base)
    bits = "".join(f"{ord(c):08b}" for c in message)
    flat = arr.flatten()
    for i, bit in enumerate(bits):
        if i >= len(flat):
            break
        flat[i] = (flat[i] & 0xFE) | int(bit)
    stego = flat.reshape(arr.shape)
    out = Image.fromarray(stego).convert("RGB")
    path = tmp_path / "stego.png"
    out.save(path)
    return path


def make_plain_image(tmp_path: Path, size: Tuple[int, int] = (600, 400)) -> Path:
    """Create a plain image for structural tests."""
    image = Image.new("RGB", size, color=(240, 240, 240))
    path = tmp_path / "plain.png"
    image.save(path)
    return path
