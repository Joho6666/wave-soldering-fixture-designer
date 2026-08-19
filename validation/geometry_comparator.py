"""Geometry comparison engine for fixture accuracy validation."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

from validation.manual_dxf_parser import ManualFixtureData, CircleFeature


@dataclass
class PolygonComparisonResult:
    iou: float = 0.0
    hausdorff_distance_mm: float = 0.0
    area_difference_mm2: float = 0.0
    perimeter_difference_mm: float = 0.0
    max_boundary_deviation_mm: float = 0.0


@dataclass
class CircleComparisonResult:
    expected_x: float = 0.0
    expected_y: float = 0.0
    expected_diameter: float = 0.0
    generated_x: float = 0.0
    generated_y: float = 0.0
    generated_diameter: float = 0.0
    center_error_mm: float = 0.0
    diameter_error_mm: float = 0.0


@dataclass
class MultiPolygonComparisonResult:
    expected_count: int = 0
    generated_count: int = 0
    matched_pairs: int = 0
    unmatched_expected: int = 0
    unmatched_generated: int = 0
    over_segmentation: bool = False
    under_segmentation: bool = False
    average_iou: float = 0.0
    average_hausdorff_mm: float = 0.0
    per_pair: list[PolygonComparisonResult] = field(default_factory=list)


@dataclass
class ComparisonReport:
    case_id: str = ""
    sink_region: PolygonComparisonResult | None = None
    fixture_outline: PolygonComparisonResult | None = None
    locating_pins: list[CircleComparisonResult] = field(default_factory=list)
    clamp_holes: list[CircleComparisonResult] = field(default_factory=list)
    barrier_mount_holes: list[CircleComparisonResult] = field(default_factory=list)
    spring_clips: list[CircleComparisonResult] = field(default_factory=list)
    keepout_regions: MultiPolygonComparisonResult | None = None
    solder_regions: MultiPolygonComparisonResult | None = None
    rails: MultiPolygonComparisonResult | None = None
    solder_barriers: MultiPolygonComparisonResult | None = None
    diagnostics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _to_serializable(asdict(self))


def _to_serializable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 6)
    return obj


class GeometryComparator:
    """Compare auto-generated fixture geometry against manual reference."""

    def compare_polygon(self, expected: Polygon | None, generated: Polygon | None) -> PolygonComparisonResult:
        result = PolygonComparisonResult()
        if expected is None or generated is None:
            return result
        if expected.is_empty or generated.is_empty:
            return result

        try:
            intersection_area = expected.intersection(generated).area
            union_area = expected.union(generated).area
            result.iou = intersection_area / union_area if union_area > 0 else 0.0
        except Exception:
            result.iou = 0.0

        try:
            result.hausdorff_distance_mm = expected.hausdorff_distance(generated)
        except Exception:
            result.hausdorff_distance_mm = float("inf")

        result.area_difference_mm2 = abs(expected.area - generated.area)
        result.perimeter_difference_mm = abs(expected.length - generated.length)

        try:
            sym_diff = expected.symmetric_difference(generated)
            if not sym_diff.is_empty:
                result.max_boundary_deviation_mm = _max_boundary_deviation(expected, generated)
        except Exception:
            pass

        return result

    def compare_circles(
        self,
        expected: list[CircleFeature],
        generated: list[dict[str, Any]],
    ) -> list[CircleComparisonResult]:
        results: list[CircleComparisonResult] = []
        gen_used: set[int] = set()

        for exp in expected:
            best_idx = -1
            best_dist = float("inf")
            for i, gen in enumerate(generated):
                if i in gen_used:
                    continue
                dist = math.hypot(exp.x - gen["x"], exp.y - gen["y"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i

            if best_idx >= 0 and best_dist < 50.0:
                gen_used.add(best_idx)
                gen = generated[best_idx]
                results.append(CircleComparisonResult(
                    expected_x=exp.x,
                    expected_y=exp.y,
                    expected_diameter=exp.diameter,
                    generated_x=gen["x"],
                    generated_y=gen["y"],
                    generated_diameter=gen.get("diameter", 0),
                    center_error_mm=best_dist,
                    diameter_error_mm=abs(exp.diameter - gen.get("diameter", 0)),
                ))
            else:
                results.append(CircleComparisonResult(
                    expected_x=exp.x,
                    expected_y=exp.y,
                    expected_diameter=exp.diameter,
                    center_error_mm=float("inf"),
                    diameter_error_mm=float("inf"),
                ))

        return results

    def compare_multi_polygon(
        self,
        expected_polys: list[Polygon],
        generated_polys: list[Polygon],
    ) -> MultiPolygonComparisonResult:
        result = MultiPolygonComparisonResult(
            expected_count=len(expected_polys),
            generated_count=len(generated_polys),
        )

        if not expected_polys or not generated_polys:
            result.unmatched_expected = len(expected_polys)
            result.unmatched_generated = len(generated_polys)
            return result

        gen_used: set[int] = set()
        pairs: list[tuple[Polygon, Polygon]] = []

        for exp_poly in expected_polys:
            best_idx = -1
            best_iou = 0.0
            for i, gen_poly in enumerate(generated_polys):
                if i in gen_used:
                    continue
                try:
                    inter = exp_poly.intersection(gen_poly).area
                    union = exp_poly.union(gen_poly).area
                    iou = inter / union if union > 0 else 0.0
                except Exception:
                    iou = 0.0
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            if best_idx >= 0 and best_iou > 0.01:
                gen_used.add(best_idx)
                pairs.append((exp_poly, generated_polys[best_idx]))
            else:
                if best_idx >= 0:
                    centroid_dist = exp_poly.centroid.distance(generated_polys[best_idx].centroid)
                    if centroid_dist < max(math.sqrt(exp_poly.area), 10.0):
                        gen_used.add(best_idx)
                        pairs.append((exp_poly, generated_polys[best_idx]))

        result.matched_pairs = len(pairs)
        result.unmatched_expected = len(expected_polys) - len(pairs)
        result.unmatched_generated = len(generated_polys) - len(gen_used)

        if len(expected_polys) < len(generated_polys) and len(pairs) < len(generated_polys):
            result.over_segmentation = True
        if len(expected_polys) > len(generated_polys) and len(pairs) < len(expected_polys):
            result.under_segmentation = True

        pair_results: list[PolygonComparisonResult] = []
        for exp_p, gen_p in pairs:
            pair_results.append(self.compare_polygon(exp_p, gen_p))

        result.per_pair = pair_results
        if pair_results:
            result.average_iou = sum(p.iou for p in pair_results) / len(pair_results)
            result.average_hausdorff_mm = sum(p.hausdorff_distance_mm for p in pair_results) / len(pair_results)

        return result

    def full_compare(
        self,
        manual: ManualFixtureData,
        auto_data: dict[str, Any],
        case_id: str = "",
    ) -> ComparisonReport:
        report = ComparisonReport(case_id=case_id)

        if manual.sink_region:
            auto_sink = auto_data.get("sink_area")
            if auto_sink is not None:
                manual_sink_union = unary_union(manual.sink_region) if len(manual.sink_region) > 1 else manual.sink_region[0]
                report.sink_region = self.compare_polygon(manual_sink_union, auto_sink)
            else:
                report.diagnostics.append("Auto-generated data missing sink_area")

        if manual.fixture_outline:
            auto_outline = auto_data.get("fixture_outline")
            if auto_outline is not None:
                manual_outline_union = unary_union(manual.fixture_outline) if len(manual.fixture_outline) > 1 else manual.fixture_outline[0]
                report.fixture_outline = self.compare_polygon(manual_outline_union, auto_outline)

        report.locating_pins = self.compare_circles(
            manual.locating_pins,
            auto_data.get("pins", []),
        )
        report.clamp_holes = self.compare_circles(
            manual.clamp_holes,
            auto_data.get("clips", []),
        )
        report.barrier_mount_holes = self.compare_circles(
            manual.barrier_mount_holes,
            auto_data.get("solder_barrier_mount_holes", []),
        )
        report.spring_clips = self.compare_circles(
            manual.spring_clips,
            auto_data.get("spring_clips", []),
        )

        if manual.keepout_regions:
            auto_keepouts = auto_data.get("keepout_zones", [])
            if isinstance(auto_keepouts, list):
                report.keepout_regions = self.compare_multi_polygon(manual.keepout_regions, auto_keepouts)

        if manual.solder_regions:
            auto_solders = auto_data.get("solder_windows", [])
            if isinstance(auto_solders, list):
                report.solder_regions = self.compare_multi_polygon(manual.solder_regions, auto_solders)

        if manual.rails:
            auto_rails = auto_data.get("rails", [])
            if isinstance(auto_rails, list):
                report.rails = self.compare_multi_polygon(manual.rails, auto_rails)

        if manual.solder_barriers:
            auto_barriers = auto_data.get("solder_barriers", [])
            if isinstance(auto_barriers, list):
                report.solder_barriers = self.compare_multi_polygon(manual.solder_barriers, auto_barriers)

        return report

    @staticmethod
    def save_report(report: ComparisonReport, output_dir: str | Path) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "comparison.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        md_path = output_dir / "comparison.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(_render_markdown(report))


def _max_boundary_deviation(poly_a: Polygon, poly_b: Polygon) -> float:
    max_dev = 0.0
    try:
        coords_a = list(poly_a.exterior.coords)
        for pt in coords_a:
            p = Point(pt)
            d = p.distance(poly_b.exterior)
            if d > max_dev:
                max_dev = d
        coords_b = list(poly_b.exterior.coords)
        for pt in coords_b:
            p = Point(pt)
            d = p.distance(poly_a.exterior)
            if d > max_dev:
                max_dev = d
    except Exception:
        pass
    return max_dev


def _render_markdown(report: ComparisonReport) -> str:
    lines = [f"# Geometry Comparison Report — {report.case_id or 'Unknown'}", ""]

    if report.sink_region:
        s = report.sink_region
        lines.append("## Sink Region")
        lines.append(f"- IoU: {s.iou:.4f}")
        lines.append(f"- Hausdorff Distance: {s.hausdorff_distance_mm:.3f} mm")
        lines.append(f"- Area Difference: {s.area_difference_mm2:.2f} mm²")
        lines.append(f"- Max Boundary Deviation: {s.max_boundary_deviation_mm:.3f} mm")
        lines.append("")

    if report.fixture_outline:
        s = report.fixture_outline
        lines.append("## Fixture Outline")
        lines.append(f"- IoU: {s.iou:.4f}")
        lines.append(f"- Hausdorff Distance: {s.hausdorff_distance_mm:.3f} mm")
        lines.append("")

    for label, circles in [
        ("Locating Pins", report.locating_pins),
        ("Clamp Holes", report.clamp_holes),
        ("Barrier Mount Holes", report.barrier_mount_holes),
        ("Spring Clips", report.spring_clips),
    ]:
        if circles:
            lines.append(f"## {label}")
            lines.append(f"- Count: {len(circles)}")
            valid = [c for c in circles if not math.isinf(c.center_error_mm)]
            if valid:
                avg_center = sum(c.center_error_mm for c in valid) / len(valid)
                avg_dia = sum(c.diameter_error_mm for c in valid) / len(valid)
                lines.append(f"- Avg Center Error: {avg_center:.4f} mm")
                lines.append(f"- Avg Diameter Error: {avg_dia:.4f} mm")
            unmatched = len(circles) - len(valid)
            if unmatched > 0:
                lines.append(f"- Unmatched: {unmatched}")
            lines.append("")

    for label, mp_result in [
        ("BOT Keepout Regions", report.keepout_regions),
        ("TOP Solder Windows", report.solder_regions),
        ("Rails", report.rails),
        ("Solder Barriers", report.solder_barriers),
    ]:
        if mp_result:
            lines.append(f"## {label}")
            lines.append(f"- Expected: {mp_result.expected_count}, Generated: {mp_result.generated_count}")
            lines.append(f"- Matched Pairs: {mp_result.matched_pairs}")
            if mp_result.over_segmentation:
                lines.append("- ⚠️ Over-segmentation detected")
            if mp_result.under_segmentation:
                lines.append("- ⚠️ Under-segmentation detected")
            if mp_result.per_pair:
                lines.append(f"- Avg IoU: {mp_result.average_iou:.4f}")
                lines.append(f"- Avg Hausdorff: {mp_result.average_hausdorff_mm:.3f} mm")
            lines.append("")

    if report.diagnostics:
        lines.append("## Diagnostics")
        for d in report.diagnostics:
            lines.append(f"- {d}")
        lines.append("")

    return "\n".join(lines)
