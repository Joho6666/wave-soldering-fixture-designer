"""Sink, fixture body, handholds, rails and solder barriers."""
from __future__ import annotations

import math
from typing import Any

from shapely import make_valid
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union


def generate_sink_region_with_relief(outline: Polygon, params: dict[str, Any]) -> Polygon:
    sink_base = outline.buffer(params["sinkClearanceMm"], join_style="round")
    radius = params["filletRadiusMm"]

    relief_circles = []
    ext_coords = list(outline.exterior.coords)[:-1]
    n = len(ext_coords)
    is_ccw = outline.exterior.is_ccw
    for i in range(n):
        p_prev = ext_coords[i - 1]
        p_curr = ext_coords[i]
        p_next = ext_coords[(i + 1) % n]

        v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        len1 = math.hypot(v1[0], v1[1])
        len2 = math.hypot(v2[0], v2[1])
        if len1 > 1e-4 and len2 > 1e-4:
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            is_convex = (cross > 1e-4) if is_ccw else (cross < -1e-4)
            if is_convex:
                relief_circles.append(Point(p_curr[0], p_curr[1]).buffer(radius))

    if relief_circles:
        combined_relief = unary_union(relief_circles)
        sink_base = make_valid(sink_base.union(combined_relief))
        if isinstance(sink_base, MultiPolygon):
            sink_base = max(sink_base.geoms, key=lambda g: g.area)

    return sink_base


def fixture_body(sink_region: Polygon, params: dict[str, Any]) -> Polygon:
    min_x, min_y, max_x, max_y = sink_region.bounds
    margin_x = params["fixtureMarginXmm"]
    margin_y = params["fixtureMarginYmm"]
    step = params.get("fixtureSizeRoundStepMm", 5.0)
    raw_left = min_x - margin_x
    raw_bot = min_y - margin_y
    raw_right = max_x + margin_x
    raw_top = max_y + margin_y
    snap_left = math.floor(raw_left / step) * step
    snap_bot = math.floor(raw_bot / step) * step
    snap_right = math.ceil(raw_right / step) * step
    snap_top = math.ceil(raw_top / step) * step
    corner_r = params["fixtureCornerRadiusMm"]
    fixture_box = box(snap_left, snap_bot, snap_right, snap_top)
    body = fixture_box.buffer(-corner_r, join_style="round").buffer(corner_r, join_style="round")
    valid = make_valid(body)
    return max(valid.geoms, key=lambda g: g.area) if isinstance(valid, MultiPolygon) else valid


def handholds(sink_region: Polygon, params: dict[str, Any]) -> list[Polygon]:
    min_x, min_y, max_x, max_y = sink_region.bounds
    w = params["handholdWidthMm"]
    h = params["handholdHeightMm"]
    overlap = params["handholdOverlapMm"]
    radius = min(max(params.get("handholdCornerRadiusMm", 2.0), 0.0), w / 2 - 0.1, h / 2 - 0.1)
    center_y = (min_y + max_y) / 2

    left_box = box(min_x - w + overlap, center_y - h / 2, min_x + overlap, center_y + h / 2)
    right_box = box(max_x - overlap, center_y - h / 2, max_x + w - overlap, center_y + h / 2)

    if radius > 0:
        left = left_box.buffer(-radius, join_style="round").buffer(radius, join_style="round")
        right = right_box.buffer(-radius, join_style="round").buffer(radius, join_style="round")
    else:
        left, right = left_box, right_box

    left = make_valid(left)
    right = make_valid(right)
    return [
        max(left.geoms, key=lambda g: g.area) if isinstance(left, MultiPolygon) else left,
        max(right.geoms, key=lambda g: g.area) if isinstance(right, MultiPolygon) else right,
    ]


def rails_and_barriers(body: Polygon, params: dict[str, Any]) -> tuple[list[Polygon], list[Polygon], list[dict[str, Any]]]:
    min_x, min_y, max_x, max_y = body.bounds
    rail_w = params["railWidthMm"]
    top_rail = box(min_x, max_y - rail_w, max_x, max_y)
    bot_rail = box(min_x, min_y, max_x, min_y + rail_w)

    barrier_w = params["solderBarrierWidthMm"]
    left_barrier = box(min_x, min_y + rail_w, min_x + barrier_w, max_y - rail_w)
    right_barrier = box(max_x - barrier_w, min_y + rail_w, max_x, max_y - rail_w)

    mount_holes = []
    barrier_y_start = min_y + rail_w + 15
    barrier_y_end = max_y - rail_w - 15
    barrier_height_span = barrier_y_end - barrier_y_start
    mount_dia = float(params.get("barrierMountHoleDiameterMm", 3.2))

    if barrier_height_span > 20:
        y_steps = [barrier_y_start, barrier_y_start + barrier_height_span / 2, barrier_y_end]
    else:
        y_steps = [(min_y + max_y) / 2]

    for i, y in enumerate(y_steps):
        mount_holes.append({
            "id": f"barrier-mount-left-{i+1}",
            "x": round(min_x + barrier_w / 2, 3),
            "y": round(y, 3),
            "diameter": mount_dia,
        })
        mount_holes.append({
            "id": f"barrier-mount-right-{i+1}",
            "x": round(max_x - barrier_w / 2, 3),
            "y": round(y, 3),
            "diameter": mount_dia,
        })

    return [top_rail, bot_rail], [left_barrier, right_barrier], mount_holes
