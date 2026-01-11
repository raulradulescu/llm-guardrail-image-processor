"""Visual overlay utilities for marking flagged regions in images."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


@dataclass
class FlaggedRegion:
    """Represents a flagged region in an image."""

    x: int
    y: int
    width: int
    height: int
    label: str
    severity: float  # 0.0 - 1.0
    module: str


# Color scheme based on severity
SEVERITY_COLORS = {
    "low": (255, 193, 7, 180),  # Yellow with alpha
    "medium": (255, 152, 0, 180),  # Orange with alpha
    "high": (244, 67, 54, 180),  # Red with alpha
}

# Module-specific label prefixes
MODULE_LABELS = {
    "text_extraction": "TEXT",
    "hidden_text": "HIDDEN",
    "frequency_analysis": "FREQ",
    "steganography": "STEGO",
    "structural": "STRUCT",
}


def get_severity_color(severity: float) -> Tuple[int, int, int, int]:
    """Get color based on severity level."""
    if severity < 0.3:
        return SEVERITY_COLORS["low"]
    elif severity < 0.6:
        return SEVERITY_COLORS["medium"]
    else:
        return SEVERITY_COLORS["high"]


def get_severity_outline(severity: float) -> Tuple[int, int, int]:
    """Get outline color (solid, no alpha) based on severity."""
    if severity < 0.3:
        return (255, 193, 7)  # Yellow
    elif severity < 0.6:
        return (255, 152, 0)  # Orange
    else:
        return (244, 67, 54)  # Red


def draw_flagged_regions(
    image: Image.Image,
    regions: List[FlaggedRegion],
    show_labels: bool = True,
    show_legend: bool = True,
) -> Image.Image:
    """Draw visual overlays on flagged regions.

    Args:
        image: Original PIL Image
        regions: List of FlaggedRegion objects to highlight
        show_labels: Whether to show labels on each region
        show_legend: Whether to show a legend at the bottom

    Returns:
        New PIL Image with overlays drawn
    """
    # Create a copy with alpha channel for transparency
    marked = image.convert("RGBA")
    overlay = Image.new("RGBA", marked.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Draw each flagged region
    for region in regions:
        color = get_severity_color(region.severity)
        outline = get_severity_outline(region.severity)

        # Draw semi-transparent fill
        draw.rectangle(
            [region.x, region.y, region.x + region.width, region.y + region.height],
            fill=color,
            outline=outline,
            width=2,
        )

        # Draw label if enabled
        if show_labels:
            module_prefix = MODULE_LABELS.get(region.module, region.module[:5].upper())
            label_text = f"{module_prefix}: {region.label}"

            # Calculate label position (above the region if possible)
            label_y = region.y - 18
            if label_y < 0:
                label_y = region.y + region.height + 2

            # Draw label background
            bbox = draw.textbbox((region.x, label_y), label_text, font=small_font)
            padding = 2
            draw.rectangle(
                [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding],
                fill=(0, 0, 0, 200),
            )
            draw.text((region.x, label_y), label_text, fill=(255, 255, 255, 255), font=small_font)

    # Composite the overlay onto the marked image
    marked = Image.alpha_composite(marked, overlay)

    # Draw legend if enabled and there are regions
    if show_legend and regions:
        marked = _draw_legend(marked, regions, font)

    return marked.convert("RGB")


def _draw_legend(image: Image.Image, regions: List[FlaggedRegion], font) -> Image.Image:
    """Draw a legend showing module scores."""
    # Group regions by module and get max severity per module
    module_scores = {}
    for region in regions:
        if region.module not in module_scores:
            module_scores[region.module] = region.severity
        else:
            module_scores[region.module] = max(module_scores[region.module], region.severity)

    if not module_scores:
        return image

    # Calculate legend dimensions
    legend_height = 25 + len(module_scores) * 18
    legend_width = 200

    # Create new image with space for legend
    new_height = image.height + legend_height
    result = Image.new("RGBA", (image.width, new_height), (40, 40, 40, 255))
    result.paste(image, (0, 0))

    draw = ImageDraw.Draw(result)

    # Draw legend title
    title_y = image.height + 5
    draw.text((10, title_y), "Detection Summary:", fill=(255, 255, 255, 255), font=font)

    # Draw each module score
    y_offset = title_y + 18
    for module, severity in sorted(module_scores.items()):
        color = get_severity_outline(severity)
        module_label = MODULE_LABELS.get(module, module)
        severity_text = f"{module_label}: {severity:.2f}"

        # Draw color indicator
        draw.rectangle([10, y_offset + 2, 20, y_offset + 12], fill=color)
        draw.text((25, y_offset), severity_text, fill=(255, 255, 255, 255), font=font)
        y_offset += 18

    return result


def extract_text_regions(
    image: Image.Image,
    languages: Optional[List[str]] = None,
    tesseract_cmd: Optional[str] = None,
) -> List[FlaggedRegion]:
    """Extract text region bounding boxes from OCR data.

    Returns list of FlaggedRegion objects for each detected text block.
    """
    try:
        import pytesseract
        from .text_analysis import configure_tesseract
    except ImportError:
        return []

    # Configure tesseract path (auto-detect on Windows if not provided)
    configure_tesseract(tesseract_cmd)

    regions = []
    lang_str = "+".join(languages) if languages else "eng"

    try:
        data = pytesseract.image_to_data(
            image, lang=lang_str, config="--psm 6", output_type=pytesseract.Output.DICT
        )

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = float(data["conf"][i]) if data["conf"][i] else 0

            # Only include text blocks with reasonable confidence
            if text and conf > 30:
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                if w > 5 and h > 5:  # Filter out tiny boxes
                    regions.append(
                        FlaggedRegion(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            label=text[:20] + "..." if len(text) > 20 else text,
                            severity=0.3,  # Base severity for text regions
                            module="text_extraction",
                        )
                    )
    except Exception:
        pass

    return regions


def create_marked_image(
    image: Image.Image,
    module_scores: dict,
    languages: Optional[List[str]] = None,
    tesseract_cmd: Optional[str] = None,
) -> Image.Image:
    """Create a marked image with overlays based on module results.

    Args:
        image: Original PIL Image
        module_scores: Dict of module results from analyzer
        languages: OCR languages for text region extraction
        tesseract_cmd: Path to tesseract executable

    Returns:
        Marked PIL Image with visual annotations
    """
    regions = []

    # Extract text regions if text module was run
    if "text_extraction" in module_scores:
        text_result = module_scores["text_extraction"]
        if text_result.get("score", 0) > 0.1:
            text_regions = extract_text_regions(image, languages, tesseract_cmd=tesseract_cmd)
            # Adjust severity based on module score
            module_severity = text_result.get("score", 0.3)
            for region in text_regions:
                region.severity = module_severity
            regions.extend(text_regions)

    # For other modules, create a full-image overlay indicator if suspicious
    for module_name in ["hidden_text", "frequency_analysis", "steganography", "structural"]:
        if module_name in module_scores:
            result = module_scores[module_name]
            score = result.get("score", 0)
            if score > 0.3:  # Only mark if suspicious
                # Add a corner indicator for full-image detections
                regions.append(
                    FlaggedRegion(
                        x=image.width - 80,
                        y=10 + len([r for r in regions if r.module != "text_extraction"]) * 25,
                        width=70,
                        height=20,
                        label=f"{score:.2f}",
                        severity=score,
                        module=module_name,
                    )
                )

    if not regions:
        return image

    return draw_flagged_regions(image, regions, show_labels=True, show_legend=True)
