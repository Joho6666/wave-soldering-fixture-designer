"""PCB Component Semantic Detection Layer.

Detects BOT SMD component regions from bottom silkscreen (GBO) and
through-hole component clusters from PTH drill hits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from app.models.geometry import DrillHit, PCBGeometry, ThroughHoleComponent


@dataclass(frozen=True)
class ComponentRegion:
    id: str
    centroid_x: float
    centroid_y: float
    bbox: tuple[float, float, float, float]
    area: float
    layer_side: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "centroidX": self.centroid_x,
            "centroidY": self.centroid_y,
            "bbox": list(self.bbox),
            "area": round(self.area, 3),
            "layerSide": self.layer_side,
        }


@dataclass(frozen=True)
class ThroughHoleCluster:
    id: str
    centroid_x: float
    centroid_y: float
    hole_count: int
    hole_ids: tuple[str, ...]
    convex_hull_wkt: str
    total_area: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "centroidX": self.centroid_x,
            "centroidY": self.centroid_y,
            "holeCount": self.hole_count,
            "holeIds": list(self.hole_ids),
            "convexHullWkt": self.convex_hull_wkt,
            "totalArea": round(self.total_area, 3),
        }


def detect_bot_components(pcb: PCBGeometry) -> list[ComponentRegion]:
    """Detect BOT SMD component regions from bottom silkscreen geometry."""
    bot_silk = pcb.bottom_silkscreen
    if bot_silk is None or bot_silk.is_empty:
        return []

    polygons: list[Polygon] = []
    if isinstance(bot_silk, Polygon):
        polygons = [bot_silk]
    elif isinstance(bot_silk, MultiPolygon):
        polygons = list(bot_silk.geoms)
    elif isinstance(bot_silk, GeometryCollection):
        polygons = [g for g in bot_silk.geoms if isinstance(g, Polygon)]

    regions: list[ComponentRegion] = []
    min_area = 1.0

    for idx, poly in enumerate(polygons):
        if poly.is_empty or poly.area < min_area:
            continue
        if not pcb.outline.intersects(poly):
            continue
        centroid = poly.centroid
        regions.append(ComponentRegion(
            id=f"bot-comp-{idx + 1}",
            centroid_x=round(centroid.x, 3),
            centroid_y=round(centroid.y, 3),
            bbox=tuple(round(v, 3) for v in poly.bounds),
            area=poly.area,
            layer_side="bottom",
        ))

    return regions


def _is_pth(hole: DrillHit) -> bool:
    if getattr(hole, "kind", "hole") == "slot":
        return False
    return hole.plated is True or (hole.plated is None and hole.diameter_mm < 2.0)


def _cluster_pth(holes: list[DrillHit], eps_mm: float, min_holes: int) -> list[list[DrillHit]]:
    if len(holes) < min_holes:
        return []
    assigned = [False] * len(holes)
    clusters: list[list[DrillHit]] = []
    for i in range(len(holes)):
        if assigned[i]:
            continue
        cluster_idx = [i]
        assigned[i] = True
        queue = [i]
        while queue:
            current = queue.pop(0)
            hc = holes[current]
            for j in range(len(holes)):
                if assigned[j]:
                    continue
                hj = holes[j]
                if math.hypot(hc.x - hj.x, hc.y - hj.y) <= eps_mm:
                    assigned[j] = True
                    cluster_idx.append(j)
                    queue.append(j)
        if len(cluster_idx) >= min_holes:
            clusters.append([holes[k] for k in cluster_idx])
    return clusters


def detect_through_hole_clusters(
    pcb: PCBGeometry,
    eps_mm: float = 5.0,
    min_holes: int = 2,
) -> list[ThroughHoleCluster]:
    """Cluster PTH drill hits by proximity to identify through-hole component groups."""
    pth_holes = [h for h in pcb.holes if _is_pth(h)]
    clusters_raw = _cluster_pth(pth_holes, eps_mm, min_holes)
    results: list[ThroughHoleCluster] = []
    for idx, holes_in_cluster in enumerate(clusters_raw):
        points = [Point(h.x, h.y) for h in holes_in_cluster]
        mp = unary_union(points)
        hull = mp.convex_hull
        centroid = hull.centroid
        results.append(ThroughHoleCluster(
            id=f"tht-cluster-{idx + 1}",
            centroid_x=round(centroid.x, 3),
            centroid_y=round(centroid.y, 3),
            hole_count=len(holes_in_cluster),
            hole_ids=tuple(h.id for h in holes_in_cluster),
            convex_hull_wkt=hull.wkt,
            total_area=round(hull.area, 3) if hull.geom_type == "Polygon" else 0.0,
        ))
    return results


def detect_through_hole_components(
    pcb: PCBGeometry,
    eps_mm: float = 5.0,
) -> list[ThroughHoleComponent]:
    """Cluster including isolated PTH pins. Slots are never included."""
    pth_holes = [h for h in pcb.holes if _is_pth(h)]
    groups = _cluster_pth(pth_holes, eps_mm, min_holes=1)
    return [classify_through_hole_group(group, f"tht-{idx + 1}") for idx, group in enumerate(groups)]


def classify_through_hole_group(holes: list[DrillHit], cluster_id: str) -> ThroughHoleComponent:
    xs = [h.x for h in holes]
    ys = [h.y for h in holes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    n = len(holes)

    if n == 1:
        return ThroughHoleComponent(
            id=cluster_id,
            hole_ids=tuple(h.id for h in holes),
            pad_ids=tuple(f"pad-{h.id}" for h in holes),
            centroid=(round(cx, 3), round(cy, 3)),
            bbox=(round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3)),
            inferred_pitch=None,
            inferred_rows=1,
            inferred_columns=1,
            orientation=0.0,
            confidence=0.70,
            component_type="unknown",
        )

    span_x = max_x - min_x
    span_y = max_y - min_y
    orientation = 0.0 if span_x >= span_y else 90.0
    pitch = _median_pitch(holes)
    rows, cols = _infer_rows_cols(holes, pitch, along_x=span_x >= span_y)
    kind, confidence = _classify_tht_kind(n, rows, cols, pitch, holes, span_x, span_y)

    return ThroughHoleComponent(
        id=cluster_id,
        hole_ids=tuple(h.id for h in holes),
        pad_ids=tuple(f"pad-{h.id}" for h in holes),
        centroid=(round(cx, 3), round(cy, 3)),
        bbox=(round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3)),
        inferred_pitch=round(pitch, 3) if pitch else None,
        inferred_rows=rows,
        inferred_columns=cols,
        orientation=orientation,
        confidence=confidence,
        component_type=kind,
    )


def _median_pitch(holes: list[DrillHit]) -> float | None:
    if len(holes) < 2:
        return None
    nearest: list[float] = []
    for i, h in enumerate(holes):
        dmin = min(math.hypot(h.x - o.x, h.y - o.y) for j, o in enumerate(holes) if i != j)
        if dmin > 1e-6:
            nearest.append(dmin)
    if not nearest:
        return None
    nearest.sort()
    mid = len(nearest) // 2
    if len(nearest) % 2:
        return nearest[mid]
    return (nearest[mid - 1] + nearest[mid]) / 2


def _cluster_axis(values: list[float], tol: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    count = 1
    current = ordered[0]
    for v in ordered[1:]:
        if abs(v - current) > tol:
            count += 1
            current = v
    return count


def _infer_rows_cols(holes: list[DrillHit], pitch: float | None, along_x: bool) -> tuple[int, int]:
    tol = max((pitch or 2.54) * 0.35, 0.4)
    nx = _cluster_axis([h.x for h in holes], tol)
    ny = _cluster_axis([h.y for h in holes], tol)
    if along_x:
        cols, rows = max(nx, 1), max(ny, 1)
    else:
        cols, rows = max(ny, 1), max(nx, 1)
    if rows > cols:
        rows, cols = cols, rows
    return rows, cols


def _classify_tht_kind(
    n: int,
    rows: int,
    cols: int,
    pitch: float | None,
    holes: list[DrillHit],
    span_x: float,
    span_y: float,
) -> tuple[str, float]:
    dia = sum(h.diameter_mm for h in holes) / n
    pitch_254 = pitch is not None and 2.0 <= pitch <= 3.1
    if rows == 1 and n >= 2:
        return "1xn", 0.88 if pitch else 0.78
    if rows == 2 and cols >= 2 and abs(rows * cols - n) <= 1:
        short_span = min(span_x, span_y)
        row_pitch = short_span if rows < 2 else short_span / (rows - 1)
        # DIP row spacing is typically ~7.62mm, pin headers are ~2.54mm.
        if cols >= 4 and pitch_254 and dia <= 1.2 and row_pitch >= max(5.0, (pitch or 2.54) * 1.8):
            return "dip", 0.86
        return "2xn", 0.90 if pitch else 0.80
    if n >= 6 and (rows >= 2 or cols >= 3) and dia >= 1.2:
        return "terminal_block", 0.74
    if n >= 6:
        return "connector", 0.72
    return "unknown", 0.62
