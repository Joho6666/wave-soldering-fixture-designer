"""BOT keepout / pocket generation. Semantic components first, Gerber fallback second."""
from __future__ import annotations

from typing import Any

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from app.models.geometry import FixtureRegion, PCBComponent, PCBGeometry
from app.services.fixture.semantic_adapter import bottom_keepout_components


def _has_body_geometry(comp: PCBComponent) -> bool:
    """PnP 只有质心、没有 courtyard/bbox 时禁止编造口袋。"""
    if comp.courtyard is not None and not getattr(comp.courtyard, "is_empty", True):
        min_x, min_y, max_x, max_y = comp.courtyard.bounds
        return (max_x - min_x) >= 0.5 and (max_y - min_y) >= 0.5
    min_x, min_y, max_x, max_y = comp.bbox
    return (max_x - min_x) >= 0.5 and (max_y - min_y) >= 0.5


def generate_keepouts(
    pcb: PCBGeometry,
    params: dict[str, Any],
    review_actions: dict[str, str] | None = None,
) -> tuple[list[Polygon], list[dict[str, Any]], list[FixtureRegion]]:
    review_items: list[dict[str, Any]] = []
    semantic = bottom_keepout_components(pcb)
    if not semantic and pcb.bot_components:
        semantic = _promote_bot_regions(pcb)
    semantic = [c for c in semantic if _has_body_geometry(c)]

    if semantic:
        return _from_components(semantic, params, review_actions)

    return _gerber_fallback(pcb, params, review_actions, review_items)


def _promote_bot_regions(pcb: PCBGeometry) -> list[PCBComponent]:
    comps: list[PCBComponent] = []
    for region in pcb.bot_components:
        bbox = region.bbox
        comps.append(
            PCBComponent(
                id=region.id,
                refdes=None,
                footprint=None,
                side="bottom",
                centroid_x=region.centroid_x,
                centroid_y=region.centroid_y,
                rotation=None,
                bbox=bbox,
                courtyard=box(*bbox),
                body_width_mm=bbox[2] - bbox[0],
                body_length_mm=bbox[3] - bbox[1],
                body_height_mm=None,
                component_type="smd",
                confidence=0.72,
                source="silkscreen_inference",
            )
        )
    return comps


def _from_components(
    components: list[PCBComponent],
    params: dict[str, Any],
    review_actions: dict[str, str] | None,
) -> tuple[list[Polygon], list[dict[str, Any]], list[FixtureRegion]]:
    keepouts: list[Polygon] = []
    metas: list[FixtureRegion] = []
    review_items: list[dict[str, Any]] = []
    clearance = params["keepoutClearanceMm"]
    fillet_r = params.get("keepoutInnerFilletMm", 1.5)
    default_depth = params.get("defaultPocketDepthMm", 2.0)
    vertical = params.get("componentVerticalClearanceMm", 0.5)

    for i, comp in enumerate(components):
        geom = comp.courtyard
        if geom is None or geom.is_empty:
            min_x, min_y, max_x, max_y = comp.bbox
            if max_x - min_x < 0.5 or max_y - min_y < 0.5:
                continue
            geom = box(min_x, min_y, max_x, max_y)
        buffered = geom.buffer(clearance, join_style="round")
        if fillet_r > 0:
            filleted = buffered.buffer(-fillet_r).buffer(fillet_r)
            if not filleted.is_empty:
                buffered = filleted
        polygons = list(buffered.geoms) if isinstance(buffered, MultiPolygon) else [buffered]
        height = comp.body_height_mm
        if height is not None:
            pocket_depth = height + vertical
            confidence = max(comp.confidence, 0.90)
        else:
            pocket_depth = default_depth
            confidence = min(comp.confidence, 0.78)

        for j, poly in enumerate(polygons):
            if poly.is_empty or poly.area < 1.0:
                continue
            rev_id = f"review-bot-keepout-{i+1}" if j == 0 else f"review-bot-keepout-{i+1}-{j+1}"
            rev_status = _status(review_actions, rev_id, confidence)
            if rev_status != "rejected":
                keepouts.append(poly)
                metas.append(
                    FixtureRegion(
                        id=rev_id,
                        region_type="pocket",
                        geometry=poly,
                        source_type="semantic_component",
                        source_ids=(comp.refdes or comp.id,),
                        confidence=confidence,
                        parameters={
                            "pocketDepthMm": round(pocket_depth, 3),
                            "componentHeightMm": height,
                            "sourceType": "semantic_component",
                        },
                    )
                )
            if confidence < 0.85:
                review_items.append({
                    "id": rev_id,
                    "type": "bot_keepout_region",
                    "status": rev_status,
                    "title": f"BOT 避位区 #{i+1} 确认",
                    "description": f"语义元件 {comp.refdes or comp.id} 避位（面积 {poly.area:.1f} mm²）。",
                    "confidence": confidence,
                    "geometryId": rev_id,
                    "mandatory": False,
                    "x": poly.centroid.x,
                    "y": poly.centroid.y,
                    "sourceType": "semantic_component",
                    "sourceIds": [comp.refdes or comp.id],
                })
    return keepouts, review_items, metas


def _gerber_fallback(
    pcb: PCBGeometry,
    params: dict[str, Any],
    review_actions: dict[str, str] | None,
    review_items: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, Any]], list[FixtureRegion]]:
    keepouts: list[Polygon] = []
    metas: list[FixtureRegion] = []
    bot_silk = pcb.bottom_silkscreen
    bot_mask = pcb.bottom_soldermask
    clearance = params["keepoutClearanceMm"]

    geom_candidates = []
    if bot_silk and not bot_silk.is_empty:
        geom_candidates.append(bot_silk)
    if bot_mask and not bot_mask.is_empty:
        geom_candidates.append(bot_mask)

    if not geom_candidates:
        review_items.append({
            "id": "review-bot-keepout-missing-layer",
            "type": "CONFIRM_NO_BOTTOM_SMD",
            "status": review_actions.get("review-bot-keepout-missing-layer", "pending") if review_actions else "pending",
            "title": "缺少 BOT 层数据 - 请确认本板无 BOT 贴片",
            "description": "未检测到底层丝印 (GBO) 或阻焊 (GBS) 层。若本板确实无 BOT 贴片元件，请确认放行；否则请重新指定图层。",
            "confidence": 0.4,
            "mandatory": True,
        })
        return [], review_items, metas

    combined = unary_union(geom_candidates)
    buffered = combined.buffer(clearance, join_style="round")
    fillet_r = params.get("keepoutInnerFilletMm", 1.5)
    if fillet_r > 0:
        filleted = buffered.buffer(-fillet_r).buffer(fillet_r)
        if not filleted.is_empty:
            buffered = filleted
    polygons = list(buffered.geoms) if isinstance(buffered, MultiPolygon) else [buffered]
    default_depth = params.get("defaultPocketDepthMm", 2.0)

    for i, poly in enumerate(polygons):
        if poly.is_empty or poly.area < 1.0:
            continue
        # Preserve historical auto-accept for large fallback blobs so existing
        # jobs without PnP do not suddenly require extra reviews.
        confidence = 0.90 if poly.area > 5.0 else 0.75
        rev_id = f"review-bot-keepout-{i+1}"
        rev_status = _status(review_actions, rev_id, confidence)
        if rev_status != "rejected":
            keepouts.append(poly)
            metas.append(
                FixtureRegion(
                    id=rev_id,
                    region_type="keepout",
                    geometry=poly,
                    source_type="gerber_fallback",
                    source_ids=(),
                    confidence=confidence,
                    parameters={
                        "pocketDepthMm": default_depth,
                        "sourceType": "gerber_fallback",
                    },
                )
            )
        if confidence < 0.85:
            review_items.append({
                "id": rev_id,
                "type": "bot_keepout_region",
                "status": rev_status,
                "title": f"BOT 避位区 #{i+1} 确认",
                "description": f"检测到底层元器件避位区域（面积 {poly.area:.1f} mm²），请确认是否需要下沉避位。",
                "confidence": confidence,
                "geometryId": rev_id,
                "mandatory": False,
                "x": poly.centroid.x,
                "y": poly.centroid.y,
                "sourceType": "gerber_fallback",
            })
    return keepouts, review_items, metas


def _status(review_actions: dict[str, str] | None, rev_id: str, confidence: float) -> str:
    default = "accepted" if confidence >= 0.85 else "pending"
    if review_actions:
        return review_actions.get(rev_id, default)
    return default
