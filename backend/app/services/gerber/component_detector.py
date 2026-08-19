"""PCB Component Semantic Detection Layer.

Detects BOT SMD component regions from bottom silkscreen (GBO) and
through-hole component clusters from PTH drill hits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import MultiPolygon, Point, Polygon, GeometryCollection
from shapely.ops import unary_union

from app.models.geometry import DrillHit, PCBGeometry


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


def detect_through_hole_clusters(
    pcb: PCBGeometry,
    eps_mm: float = 5.0,
    min_holes: int = 2,
) -> list[ThroughHoleCluster]:
    """Cluster PTH drill hits by proximity to identify through-hole component groups."""
    pth_holes = [
        h for h in pcb.holes
        if h.plated is True or (h.plated is None and h.diameter_mm < 2.0)
    ]
    if len(pth_holes) < min_holes:
        return []

    assigned = [False] * len(pth_holes)
    clusters_raw: list[list[int]] = []

    for i in range(len(pth_holes)):
        if assigned[i]:
            continue
        cluster = [i]
        assigned[i] = True
        queue = [i]
        while queue:
            current = queue.pop(0)
            hc = pth_holes[current]
            for j in range(len(pth_holes)):
                if assigned[j]:
                    continue
                hj = pth_holes[j]
                dist = math.hypot(hc.x - hj.x, hc.y - hj.y)
                if dist <= eps_mm:
                    assigned[j] = True
                    cluster.append(j)
                    queue.append(j)
        if len(cluster) >= min_holes:
            clusters_raw.append(cluster)

    results: list[ThroughHoleCluster] = []
    for idx, indices in enumerate(clusters_raw):
        holes_in_cluster = [pth_holes[i] for i in indices]
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
