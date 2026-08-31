"""Clamp holes and front-panel spring clip mounting holes."""
from __future__ import annotations

from typing import Any

from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon

from app.models.geometry import PCBGeometry


def clamp_holes(sink_region: Polygon, params: dict[str, Any]) -> list[dict[str, Any]]:
    min_x, min_y, max_x, max_y = sink_region.bounds
    offset = params["clampOffsetMm"]
    diameter = params["clampHoleDiameterMm"]
    points = [
        (min_x + offset, max_y + offset),
        (max_x - offset, max_y + offset),
        (min_x + offset, min_y - offset),
        (max_x - offset, min_y - offset),
    ]
    return [
        {"id": f"clamp-{index+1}", "x": round(x, 3), "y": round(y, 3), "diameter": diameter}
        for index, (x, y) in enumerate(points)
    ]


def front_panel_spring_clips(
    pcb: PCBGeometry,
    params: dict[str, Any],
    review_actions: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clips: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    top_silk = pcb.top_silkscreen
    radius = params["springClipRadiusMm"]
    diameter = radius * 2

    if top_silk is None or top_silk.is_empty:
        review_items.append({
            "id": "review-spring-clip-no-gto",
            "type": "CONFIRM_NO_SPRING_CLIP_REQUIRED",
            "status": review_actions.get("review-spring-clip-no-gto", "pending") if review_actions else "pending",
            "title": "缺少 GTO 层 - 请确认无需弹簧卡安装孔",
            "description": "未检测到顶层丝印 (GTO) 数据。若本板无需前挡板弹簧卡安装孔，请确认放行；否则请重新指定 GTO 图层。",
            "confidence": 0.3,
            "mandatory": True,
        })
        return [], review_items

    polygons: list[Polygon] = []
    if isinstance(top_silk, (Polygon, MultiPolygon)):
        polygons = list(top_silk.geoms) if isinstance(top_silk, MultiPolygon) else [top_silk]
    elif isinstance(top_silk, GeometryCollection):
        for g in top_silk.geoms:
            if isinstance(g, Polygon):
                polygons.append(g)
            elif isinstance(g, MultiPolygon):
                polygons.extend(list(g.geoms))
            elif isinstance(g, (LineString, MultiLineString)):
                buf = g.buffer(0.1)
                if isinstance(buf, Polygon):
                    polygons.append(buf)
                elif isinstance(buf, MultiPolygon):
                    polygons.extend(list(buf.geoms))
    elif isinstance(top_silk, (LineString, MultiLineString)):
        buf = top_silk.buffer(0.1)
        polygons = list(buf.geoms) if isinstance(buf, MultiPolygon) else [buf]

    if not polygons:
        review_items.append({
            "id": "review-spring-clip-no-regions",
            "type": "front_panel_clip",
            "status": review_actions.get("review-spring-clip-no-regions", "pending") if review_actions else "pending",
            "title": "TOP 丝印无有效区域",
            "description": "顶层丝印中未检测到有效闭合元件区域，无法定位弹簧卡安装孔。",
            "confidence": 0.4,
            "mandatory": False,
        })
        return [], review_items

    min_area = 4.0
    for i, poly in enumerate(polygons):
        if poly.area < min_area or poly.is_empty:
            continue
        cx = poly.centroid.x
        cy = poly.centroid.y
        if not pcb.outline.contains(Point(cx, cy)):
            continue
        clip_id = f"spring-clip-{i+1}"
        clips.append({
            "id": clip_id,
            "x": round(cx, 3),
            "y": round(cy, 3),
            "diameter": diameter,
        })

    if not clips:
        review_items.append({
            "id": "review-spring-clip-none-found",
            "type": "front_panel_clip",
            "status": review_actions.get("review-spring-clip-none-found", "pending") if review_actions else "pending",
            "title": "未找到弹簧卡安装位",
            "description": "顶层丝印区域均不满足弹簧卡安装条件（面积过小或超出板外形）。",
            "confidence": 0.5,
            "mandatory": False,
        })

    return clips, review_items
