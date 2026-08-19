"""Local OCR Engine for RefDes (Reference Designator) extraction from GTO silkscreen.

This module is fully OPTIONAL. If pytesseract/Tesseract is not installed,
the core fixture pipeline continues to work without OCR.

Usage:
    from app.services.ocr.refdes_ocr import extract_refdes, is_ocr_available

    if is_ocr_available():
        results = extract_refdes(top_silkscreen_geometry, pcb_bounds)
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Any

from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

_TESSERACT_AVAILABLE: bool | None = None

REFDES_PATTERN = re.compile(
    r"\b([RCUQJDLT]\d{1,4})\b",
    re.IGNORECASE,
)

DPI = 300
MM_PER_INCH = 25.4


def is_ocr_available() -> bool:
    """Check if pytesseract and Pillow are available."""
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is not None:
        return _TESSERACT_AVAILABLE
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
        pytesseract.get_tesseract_version()
        _TESSERACT_AVAILABLE = True
    except Exception:
        _TESSERACT_AVAILABLE = False
        logger.info("OCR 不可用: pytesseract 或 Tesseract 未安装, RefDes 识别跳过")
    return _TESSERACT_AVAILABLE


@dataclass
class OcrRefDesResult:
    refdes: str
    x: float
    y: float
    confidence: float
    bbox: tuple[float, float, float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "refdes": self.refdes,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "confidence": round(self.confidence, 2),
            "bbox": [round(v, 3) for v in self.bbox],
        }


def extract_refdes(
    top_silkscreen: BaseGeometry | None,
    pcb_bounds: tuple[float, float, float, float],
) -> list[OcrRefDesResult]:
    """Extract RefDes labels from top silkscreen geometry via local OCR.

    Returns empty list if OCR is not available or silkscreen is empty.
    """
    if not is_ocr_available():
        return []

    if top_silkscreen is None or top_silkscreen.is_empty:
        logger.info("OCR: 顶层丝印为空, 跳过 RefDes 提取")
        return []

    try:
        import pytesseract
        from PIL import Image, ImageDraw
    except ImportError:
        return []

    min_x, min_y, max_x, max_y = pcb_bounds
    width_mm = max_x - min_x
    height_mm = max_y - min_y

    if width_mm <= 0 or height_mm <= 0:
        return []

    px_per_mm = DPI / MM_PER_INCH
    img_w = max(int(width_mm * px_per_mm), 1)
    img_h = max(int(height_mm * px_per_mm), 1)

    img_w = min(img_w, 8000)
    img_h = min(img_h, 8000)

    actual_px_per_mm_x = img_w / width_mm
    actual_px_per_mm_y = img_h / height_mm

    img = Image.new("L", (img_w, img_h), 255)
    draw = ImageDraw.Draw(img)

    polygons: list[Polygon] = []
    if isinstance(top_silkscreen, Polygon):
        polygons = [top_silkscreen]
    elif isinstance(top_silkscreen, MultiPolygon):
        polygons = list(top_silkscreen.geoms)
    elif isinstance(top_silkscreen, GeometryCollection):
        polygons = [g for g in top_silkscreen.geoms if isinstance(g, Polygon)]

    for poly in polygons:
        if poly.is_empty:
            continue
        coords = list(poly.exterior.coords)
        px_coords = [
            (
                int((x - min_x) * actual_px_per_mm_x),
                int((max_y - y) * actual_px_per_mm_y),
            )
            for x, y in coords
        ]
        if len(px_coords) >= 3:
            draw.polygon(px_coords, fill=0, outline=0)

    try:
        ocr_data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        )
    except Exception as exc:
        logger.warning(f"OCR 执行失败: {exc}")
        return []

    results: list[OcrRefDesResult] = []
    num_items = len(ocr_data.get("text", []))

    for i in range(num_items):
        text = str(ocr_data["text"][i]).strip()
        conf = float(ocr_data["conf"][i])
        if conf < 30 or not text:
            continue

        match = REFDES_PATTERN.match(text)
        if not match:
            continue

        refdes = match.group(1).upper()
        px_x = ocr_data["left"][i] + ocr_data["width"][i] / 2
        px_y = ocr_data["top"][i] + ocr_data["height"][i] / 2

        pcb_x = min_x + px_x / actual_px_per_mm_x
        pcb_y = max_y - px_y / actual_px_per_mm_y

        bbox_x1 = min_x + ocr_data["left"][i] / actual_px_per_mm_x
        bbox_y1 = max_y - (ocr_data["top"][i] + ocr_data["height"][i]) / actual_px_per_mm_y
        bbox_x2 = min_x + (ocr_data["left"][i] + ocr_data["width"][i]) / actual_px_per_mm_x
        bbox_y2 = max_y - ocr_data["top"][i] / actual_px_per_mm_y

        results.append(OcrRefDesResult(
            refdes=refdes,
            x=pcb_x,
            y=pcb_y,
            confidence=conf / 100.0,
            bbox=(bbox_x1, bbox_y1, bbox_x2, bbox_y2),
        ))

    seen: set[str] = set()
    deduped: list[OcrRefDesResult] = []
    for r in sorted(results, key=lambda x: -x.confidence):
        if r.refdes not in seen:
            seen.add(r.refdes)
            deduped.append(r)

    logger.info(f"OCR: 提取到 {len(deduped)} 个 RefDes 标识")
    return deduped
