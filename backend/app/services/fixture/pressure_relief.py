"""Pressure relief channels from large pockets to the nearest free fixture edge."""
from __future__ import annotations

import math
from typing import Any

from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union

from app.models.geometry import FixtureRegion


def generate_pressure_relief(
    body: BaseGeometry,
    pcb_outline: BaseGeometry,
    keepouts: list[BaseGeometry],
    keepout_meta: list[FixtureRegion],
    solder_regions: list[BaseGeometry],
    locating_pins: list[dict[str, Any]],
    clamp_holes: list[dict[str, Any]],
    params: dict[str, Any],
) -> tuple[list[Polygon], list[FixtureRegion]]:
    if not params.get("pressureReliefEnabled"):
        return [], []

    min_area = float(params.get("pressureReliefMinPocketAreaMm2", 400.0))
    width = float(params.get("pressureReliefChannelWidthMm", 2.0))
    edge_clearance = float(params.get("pressureReliefEdgeClearanceMm", 3.0))
    min_web = float(params.get("minimumMaterialWebMm", 2.0))
    half = max(width / 2.0, 0.2)

    obstacles: list[BaseGeometry] = []
    if pcb_outline is not None and not pcb_outline.is_empty:
        obstacles.append(pcb_outline.buffer(min_web * 0.5))
    for s in solder_regions:
        if s is not None and not s.is_empty:
            obstacles.append(s.buffer(min_web))
    for pin in locating_pins:
        obstacles.append(Point(pin["x"], pin["y"]).buffer(float(pin.get("diameter", 3.0)) / 2.0 + min_web))
    for clamp in clamp_holes:
        obstacles.append(Point(clamp["x"], clamp["y"]).buffer(float(clamp.get("diameter", 3.4)) / 2.0 + min_web))
    blocked = unary_union(obstacles) if obstacles else None

    inner_body = body.buffer(-edge_clearance) if edge_clearance > 0 else body
    if inner_body is None or inner_body.is_empty:
        inner_body = body
    free_boundary = inner_body.boundary

    channels: list[Polygon] = []
    metas: list[FixtureRegion] = []
    for idx, pocket in enumerate(keepouts):
        if pocket is None or pocket.is_empty or pocket.area < min_area:
            continue
        try:
            p_on_pocket, p_on_edge = nearest_points(pocket.boundary, free_boundary)
        except Exception:
            continue
        start = Point(p_on_pocket.x, p_on_pocket.y)
        end = Point(p_on_edge.x, p_on_edge.y)
        if start.distance(end) < 0.5:
            continue
        inward = pocket.centroid
        dx = start.x - inward.x
        dy = start.y - inward.y
        length = math.hypot(dx, dy)
        if length > 1e-6:
            stub_len = min(half * 2.0, length * 0.25)
            stub_start = Point(start.x - dx / length * stub_len, start.y - dy / length * stub_len)
            if not pocket.contains(stub_start) and not pocket.covers(stub_start):
                stub_start = start
        else:
            stub_start = start
        spine = LineString([(stub_start.x, stub_start.y), (start.x, start.y), (end.x, end.y)])
        corridor = spine.buffer(half, cap_style="flat")
        corridor = corridor.intersection(body)
        if corridor.is_empty:
            continue
        if blocked is not None and not blocked.is_empty:
            corridor = corridor.difference(blocked)
        other_pockets = [k for j, k in enumerate(keepouts) if j != idx and k is not None and not k.is_empty]
        if other_pockets:
            corridor = corridor.difference(unary_union(other_pockets).buffer(min_web * 0.25))
        if corridor.is_empty:
            continue
        geoms = list(corridor.geoms) if corridor.geom_type == "MultiPolygon" else [corridor]
        attached = [g for g in geoms if g.geom_type == "Polygon" and not g.is_empty and g.area >= 0.5 and g.intersects(pocket)]
        if not attached:
            continue
        for g_i, geom in enumerate(attached):
            channels.append(geom)
            source = keepout_meta[idx].id if idx < len(keepout_meta) else f"pocket-{idx+1}"
            metas.append(
                FixtureRegion(
                    id=f"pressure-relief-{idx+1}-{g_i+1}",
                    region_type="pressure_relief",
                    geometry=geom,
                    source_type="manual",
                    source_ids=(source,),
                    confidence=0.85,
                    parameters={
                        "sourceType": "pressure_relief",
                        "channelWidthMm": width,
                        "fromPocket": source,
                    },
                )
            )
    return channels, metas
