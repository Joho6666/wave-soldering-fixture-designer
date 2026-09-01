"""Per-feature validation thresholds. One table, no global IoU for every feature."""
from __future__ import annotations

from typing import Any

FEATURE_KEYS = (
    "pcb_outline",
    "fixture_body",
    "sink",
    "locating_pins",
    "solder_openings",
    "keepout_regions",
    "clamps",
    "spring_clips",
    "solder_barriers",
    "handholds",
    "pressure_relief",
    "conveyor_rails",
)

# primary tells the scorer which metric family to emphasize.
THRESHOLDS: dict[str, dict[str, Any]] = {
    "pcb_outline": {
        "family": "contour",
        "pass": {"hausdorffMm": 0.80, "centroidErrorMm": 0.80, "areaErrorPercent": 5.0},
        "warn": {"hausdorffMm": 2.00, "centroidErrorMm": 2.00, "areaErrorPercent": 12.0},
    },
    "fixture_body": {
        "family": "contour",
        "pass": {"hausdorffMm": 1.00, "centroidErrorMm": 1.00, "areaErrorPercent": 6.0},
        "warn": {"hausdorffMm": 3.00, "centroidErrorMm": 2.50, "areaErrorPercent": 15.0},
    },
    "sink": {
        "family": "contour",
        "pass": {"hausdorffMm": 0.80, "centroidErrorMm": 0.80, "areaErrorPercent": 6.0, "iou": 0.92},
        "warn": {"hausdorffMm": 2.50, "centroidErrorMm": 2.00, "areaErrorPercent": 12.0, "iou": 0.75},
    },
    "locating_pins": {
        "family": "hole",
        "pass": {"centroidErrorMm": 0.40, "diameterErrorMm": 0.15},
        "warn": {"centroidErrorMm": 1.00, "diameterErrorMm": 0.30},
    },
    "clamps": {
        "family": "hole",
        "pass": {"centroidErrorMm": 0.50, "diameterErrorMm": 0.20},
        "warn": {"centroidErrorMm": 1.20, "diameterErrorMm": 0.40},
    },
    "spring_clips": {
        "family": "hole",
        "pass": {"centroidErrorMm": 0.60, "diameterErrorMm": 0.25},
        "warn": {"centroidErrorMm": 1.50, "diameterErrorMm": 0.50},
    },
    "solder_openings": {
        "family": "opening",
        "pass": {"iou": 0.92, "hausdorffMm": 1.50, "areaErrorPercent": 8.0, "centroidErrorMm": 1.00},
        "warn": {"iou": 0.75, "hausdorffMm": 4.00, "areaErrorPercent": 18.0, "centroidErrorMm": 3.00},
    },
    "keepout_regions": {
        "family": "opening",
        "pass": {"iou": 0.90, "hausdorffMm": 1.80, "areaErrorPercent": 10.0, "centroidErrorMm": 1.20},
        "warn": {"iou": 0.72, "hausdorffMm": 4.50, "areaErrorPercent": 20.0, "centroidErrorMm": 3.50},
    },
    "solder_barriers": {
        "family": "opening",
        "pass": {"iou": 0.88, "hausdorffMm": 2.00, "areaErrorPercent": 12.0},
        "warn": {"iou": 0.70, "hausdorffMm": 5.00, "areaErrorPercent": 22.0},
    },
    "handholds": {
        "family": "opening",
        "pass": {"iou": 0.88, "hausdorffMm": 2.00, "areaErrorPercent": 12.0},
        "warn": {"iou": 0.70, "hausdorffMm": 5.00, "areaErrorPercent": 22.0},
    },
    "pressure_relief": {
        "family": "opening",
        "pass": {"iou": 0.80, "hausdorffMm": 2.50, "areaErrorPercent": 20.0},
        "warn": {"iou": 0.55, "hausdorffMm": 6.00, "areaErrorPercent": 35.0},
    },
    "conveyor_rails": {
        "family": "opening",
        "pass": {"iou": 0.88, "hausdorffMm": 2.00, "areaErrorPercent": 12.0},
        "warn": {"iou": 0.70, "hausdorffMm": 5.00, "areaErrorPercent": 22.0},
    },
}


def decide_status(feature: str, metrics: dict[str, float | None], *, unmatched: int = 0, count_diff: int = 0) -> str:
    spec = THRESHOLDS[feature]
    family = spec["family"]
    pas = spec["pass"]
    warn = spec["warn"]
    if unmatched > 0:
        if family == "hole" and unmatched <= 1 and count_diff <= 1:
            return "WARNING"
        return "FAIL"

    def _ok(table: dict[str, float]) -> bool:
        for key, limit in table.items():
            value = metrics.get(key)
            if value is None:
                continue
            if key == "iou":
                if value < limit:
                    return False
            elif value > limit:
                return False
        return True

    if _ok(pas):
        return "PASS"
    if _ok(warn):
        return "WARNING"
    return "FAIL"
