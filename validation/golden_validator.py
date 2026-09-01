"""Golden fixture validator: PCB files + engineer DXF vs generated DXF."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from validation.feature_thresholds import FEATURE_KEYS, decide_status
from validation.geometry_comparator import GeometryComparator, PolygonComparisonResult
from validation.manual_dxf_parser import CircleFeature, ManualFixtureData, ManualFixtureDxfParser


CASE_STATUSES = (
    "awaiting_input",
    "awaiting_reference",
    "awaiting_reference_dxf",
    "ready",
    "passed",
    "failed",
    "review_required",
    "NOT_AVAILABLE",
)


@dataclass
class FeatureScore:
    name: str
    status: str
    iou: float | None = None
    hausdorff_mm: float | None = None
    centroid_distance_mm: float | None = None
    area_error_pct: float | None = None
    perimeter_error_pct: float | None = None
    hole_position_error_mm: float | None = None
    hole_diameter_error_mm: float | None = None
    expected_count: int = 0
    generated_count: int = 0
    unmatched_feature_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "feature": self.name,
            "status": self.status,
            "generatedCount": self.generated_count,
            "referenceCount": self.expected_count,
            "iou": self.iou,
            "hausdorffMm": self.hausdorff_mm,
            "centroidErrorMm": self.centroid_distance_mm,
            "areaErrorPercent": self.area_error_pct,
            "diameterErrorMm": self.hole_diameter_error_mm,
            "notes": self.notes,
            "name": self.name,
            "hausdorff_mm": self.hausdorff_mm,
            "centroid_distance_mm": self.centroid_distance_mm,
            "area_error_pct": self.area_error_pct,
            "hole_position_error_mm": self.hole_position_error_mm,
            "hole_diameter_error_mm": self.hole_diameter_error_mm,
            "expected_count": self.expected_count,
            "generated_count": self.generated_count,
            "unmatched_feature_count": self.unmatched_feature_count,
        }
        return payload


@dataclass
class ValidationVerdict:
    case_id: str
    status: str
    overall: str
    features: list[FeatureScore]
    created_at: str
    diagnostics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "caseId": self.case_id,
            "status": self.status,
            "overall": self.overall,
            "createdAt": self.created_at,
            "features": [f.to_dict() for f in self.features],
            "diagnostics": self.diagnostics,
        }


def _pct(expected: float, generated: float) -> float:
    if abs(expected) < 1e-9:
        return 0.0 if abs(generated) < 1e-9 else 100.0
    return abs(generated - expected) / abs(expected) * 100.0


def _union(polys: list[Polygon] | None) -> BaseGeometry | None:
    """Keep every island. Do not drop smaller polygons from a MultiPolygon."""
    items = [p for p in (polys or []) if p is not None and not p.is_empty]
    if not items:
        return None
    merged = unary_union(items)
    if merged.is_empty:
        return None
    return merged


def _as_polygon_like(value: Any) -> BaseGeometry | None:
    if value is None:
        return None
    if isinstance(value, list):
        return _union(value)
    if getattr(value, "is_empty", False):
        return None
    return value


def _score_polygon(name: str, expected: BaseGeometry | None, generated: BaseGeometry | None) -> FeatureScore:
    if expected is None and generated is None:
        return FeatureScore(name=name, status="NOT_AVAILABLE", notes=["no geometry on either side"])
    if expected is None or generated is None:
        return FeatureScore(
            name=name,
            status="FAIL",
            expected_count=0 if expected is None else 1,
            generated_count=0 if generated is None else 1,
            unmatched_feature_count=1,
            notes=["missing counterpart"],
        )
    cmp = GeometryComparator().compare_polygon(expected, generated)
    centroid = expected.centroid.distance(generated.centroid)
    area_err = _pct(expected.area, generated.area)
    peri_err = _pct(expected.length, generated.length)
    status = decide_status(
        name,
        {
            "iou": cmp.iou,
            "hausdorffMm": cmp.hausdorff_distance_mm,
            "centroidErrorMm": centroid,
            "areaErrorPercent": area_err,
        },
    )
    return FeatureScore(
        name=name,
        status=status,
        iou=cmp.iou,
        hausdorff_mm=cmp.hausdorff_distance_mm,
        centroid_distance_mm=centroid,
        area_error_pct=area_err,
        perimeter_error_pct=peri_err,
        expected_count=1,
        generated_count=1,
        unmatched_feature_count=0,
    )


def _score_multi(name: str, expected: list[Polygon], generated: list[Polygon]) -> FeatureScore:
    if not expected and not generated:
        return FeatureScore(name=name, status="NOT_AVAILABLE", notes=["no geometry on either side"])
    result = GeometryComparator().compare_multi_polygon(expected, generated)
    unmatched = result.unmatched_expected + result.unmatched_generated
    area_errors: list[float] = []
    peri_errors: list[float] = []
    centroid_errors: list[float] = []
    for exp, pair in zip(expected, result.per_pair):
        area_errors.append(_pct(1.0, 1.0 + (pair.area_difference_mm2 / max(exp.area, 1e-6))) if exp.area else 0.0)
        peri_errors.append(_pct(exp.length, exp.length + pair.perimeter_difference_mm) if exp.length else 0.0)
        centroid_errors.append(pair.hausdorff_distance_mm)
    mean_area = sum(area_errors) / len(area_errors) if area_errors else None
    status = decide_status(
        name,
        {
            "iou": result.average_iou,
            "hausdorffMm": result.average_hausdorff_mm,
            "centroidErrorMm": (sum(centroid_errors) / len(centroid_errors)) if centroid_errors else None,
            "areaErrorPercent": mean_area,
        },
        unmatched=unmatched,
        count_diff=abs(result.expected_count - result.generated_count),
    )
    return FeatureScore(
        name=name,
        status=status,
        iou=result.average_iou,
        hausdorff_mm=result.average_hausdorff_mm,
        centroid_distance_mm=sum(centroid_errors) / len(centroid_errors) if centroid_errors else None,
        area_error_pct=mean_area,
        perimeter_error_pct=sum(peri_errors) / len(peri_errors) if peri_errors else None,
        expected_count=result.expected_count,
        generated_count=result.generated_count,
        unmatched_feature_count=unmatched,
    )


def _score_holes(name: str, expected: list[CircleFeature], generated: list[dict[str, Any]]) -> FeatureScore:
    if not expected and not generated:
        return FeatureScore(name=name, status="NOT_AVAILABLE", notes=["no holes on either side"])
    results = GeometryComparator().compare_circles(expected, generated)
    unmatched = sum(1 for r in results if math.isinf(r.center_error_mm))
    unmatched += max(0, len(generated) - len(results) + unmatched)
    valid = [r for r in results if not math.isinf(r.center_error_mm)]
    pos = sum(r.center_error_mm for r in valid) / len(valid) if valid else (float("inf") if expected else 0.0)
    dia = sum(r.diameter_error_mm for r in valid) / len(valid) if valid else (float("inf") if expected else 0.0)
    count_diff = abs(len(expected) - len(generated))
    status = decide_status(
        name,
        {
            "centroidErrorMm": None if math.isinf(pos) else pos,
            "diameterErrorMm": None if math.isinf(dia) else dia,
        },
        unmatched=unmatched,
        count_diff=count_diff,
    )
    return FeatureScore(
        name=name,
        status=status,
        hole_position_error_mm=None if math.isinf(pos) else pos,
        hole_diameter_error_mm=None if math.isinf(dia) else dia,
        centroid_distance_mm=None if math.isinf(pos) else pos,
        expected_count=len(expected),
        generated_count=len(generated),
        unmatched_feature_count=unmatched + count_diff,
    )


def _as_polys(value: Any) -> list[Polygon]:
    if value is None:
        return []
    if isinstance(value, list):
        return [g for g in value if g is not None and not getattr(g, "is_empty", False)]
    if getattr(value, "is_empty", False):
        return []
    return [value]


def compare_fixture(manual: ManualFixtureData, generated: dict[str, Any], case_id: str) -> ValidationVerdict:
    pcb_outline = generated.get("pcb_outline")
    features = [
        _score_polygon("pcb_outline", _union(manual.pcb_outline), _as_polygon_like(pcb_outline)),
        _score_polygon("fixture_body", _union(manual.fixture_outline), _as_polygon_like(generated.get("fixture_outline"))),
        _score_polygon("sink", _union(manual.sink_region), _as_polygon_like(generated.get("sink_area"))),
        _score_multi("keepout_regions", list(manual.keepout_regions), _as_polys(generated.get("keepout_zones"))),
        _score_multi("solder_openings", list(manual.solder_regions), _as_polys(generated.get("solder_windows"))),
        _score_holes("locating_pins", list(manual.locating_pins), list(generated.get("pins") or [])),
        _score_holes("clamps", list(manual.clamp_holes), list(generated.get("clips") or [])),
        _score_holes("spring_clips", list(manual.spring_clips), list(generated.get("spring_clips") or [])),
        _score_multi("solder_barriers", list(manual.solder_barriers), _as_polys(generated.get("solder_barriers"))),
        _score_multi("handholds", list(manual.handholds), _as_polys(generated.get("handholds"))),
        _score_multi("pressure_relief", list(manual.pressure_relief), _as_polys(generated.get("pressure_relief_channels"))),
        _score_multi("conveyor_rails", list(manual.rails), _as_polys(generated.get("rails"))),
    ]
    comparable = [f.status for f in features if f.status != "NOT_AVAILABLE"]
    if not comparable:
        overall = "NOT_AVAILABLE"
        case_status = "awaiting_reference"
    elif "FAIL" in comparable:
        overall = "FAIL"
        case_status = "failed"
    elif "WARNING" in comparable:
        overall = "WARNING"
        case_status = "review_required"
    else:
        overall = "PASS"
        case_status = "passed"
    return ValidationVerdict(
        case_id=case_id,
        status=case_status,
        overall=overall,
        features=features,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def overlay_svg(manual: ManualFixtureData, generated: dict[str, Any]) -> str:
    ref = _union(manual.fixture_outline) or _union(manual.sink_region)
    gen = generated.get("fixture_outline") or generated.get("sink_area")
    if ref is None and gen is None:
        return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    bounds_src = [g for g in (ref, gen) if g is not None]
    minx, miny, maxx, maxy = unary_union(bounds_src).bounds
    pad = 8
    inter = ref.intersection(gen) if ref is not None and gen is not None else None
    only_gen = gen.difference(ref) if ref is not None and gen is not None else gen
    only_ref = ref.difference(gen) if ref is not None and gen is not None else ref

    def path(geom, color, opacity=0.45) -> str:
        if geom is None or geom.is_empty:
            return ""
        geoms = list(geom.geoms) if geom.geom_type in {"MultiPolygon", "GeometryCollection"} else [geom]
        parts = []
        for g in geoms:
            if g.geom_type != "Polygon":
                continue
            d = " ".join(f"{x:.3f},{y:.3f}" for x, y in g.exterior.coords)
            parts.append(f'<polygon points="{d}" fill="{color}" fill-opacity="{opacity}" stroke="{color}" stroke-width="0.2"/>')
        return "".join(parts)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx-pad} {miny-pad} {maxx-minx+2*pad} {maxy-miny+2*pad}">'
        f'<g id="generated" data-layer="generated">{path(gen, "#3b82f6", 0.28)}</g>'
        f'<g id="reference" data-layer="reference">{path(ref, "#22c55e", 0.28)}</g>'
        f'<g id="overlap" data-layer="overlap">{path(inter, "#94a3b8", 0.35)}</g>'
        f'<g id="difference" data-layer="difference">{path(only_gen, "#f59e0b", 0.55)}{path(only_ref, "#ef4444", 0.55)}</g>'
        "</svg>"
    )


def write_reports(verdict: ValidationVerdict, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "validation_report.json"
    json_path.write_text(json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        f"# Validation Report — {verdict.case_id}",
        "",
        f"- Overall: **{verdict.overall}**",
        f"- Case status: `{verdict.status}`",
        f"- Created: {verdict.created_at}",
        "",
        "| Feature | Status | IoU | Hausdorff mm | Centroid mm | Area err % | Count exp/gen | Unmatched |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in verdict.features:
        lines.append(
            f"| {f.name} | {f.status} | {_fmt(f.iou)} | {_fmt(f.hausdorff_mm)} | {_fmt(f.centroid_distance_mm)} | "
            f"{_fmt(f.area_error_pct)} | {f.expected_count}/{f.generated_count} | {f.unmatched_feature_count} |"
        )
    if verdict.diagnostics:
        lines.extend(["", "## Diagnostics", *[f"- {d}" for d in verdict.diagnostics]])
    (report_dir / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: float | None) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    return f"{value:.4f}"


def parse_reference_dxf(path: Path, mapping: dict[str, str] | None = None) -> ManualFixtureData:
    parser = ManualFixtureDxfParser(layer_mapping=mapping)
    return parser.parse(path)
