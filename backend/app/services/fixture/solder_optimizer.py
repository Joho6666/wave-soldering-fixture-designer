"""Solder opening optimizer. ThroughHoleComponent first, greedy PTH fallback second."""
from __future__ import annotations

import math
from typing import Any

from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from app.models.geometry import DrillHit, FixtureRegion, PCBGeometry, ThroughHoleComponent
from app.services.fixture.semantic_adapter import tht_components
from app.services.gerber.component_detector import detect_through_hole_components


def generate_solder_openings(
    pcb: PCBGeometry,
    params: dict[str, Any],
    review_actions: dict[str, str] | None = None,
) -> tuple[list[Polygon], list[dict[str, Any]], list[FixtureRegion]]:
    holes = pcb.holes
    pth_holes = [
        h for h in holes
        if getattr(h, "kind", "hole") != "slot"
        and (h.plated is True or (h.plated is None and h.diameter_mm < 2.0))
    ]
    if not pth_holes:
        return [], [_missing_pth_review(review_actions)], []

    clusters = tht_components(pcb)
    if not clusters:
        clusters = detect_through_hole_components(pcb)

    if clusters:
        regions, reviews, metas = _from_tht(pcb, clusters, pth_holes, params, review_actions)
        if regions:
            return regions, reviews, metas

    regions, reviews, metas = _greedy_fallback(pcb, pth_holes, params, review_actions)
    regions, metas = _merge_close(regions, metas, params)
    return regions, reviews, metas


def _missing_pth_review(review_actions: dict[str, str] | None) -> dict[str, Any]:
    return {
        "id": "review-top-solder-no-pth",
        "type": "CONFIRM_NO_TOP_THT",
        "status": review_actions.get("review-top-solder-no-pth", "pending") if review_actions else "pending",
        "title": "未检测到 PTH 通孔 - 请确认无需上锡窗口",
        "description": "未检测到明确的 PTH 通孔引脚。若本板确实无插件焊接需求，请确认放行；否则请重新指定钻孔文件。",
        "confidence": 0.5,
        "mandatory": True,
    }


def _from_tht(
    pcb: PCBGeometry,
    clusters: list[ThroughHoleComponent],
    pth_holes: list[DrillHit],
    params: dict[str, Any],
    review_actions: dict[str, str] | None,
) -> tuple[list[Polygon], list[dict[str, Any]], list[FixtureRegion]]:
    by_id = {h.id: h for h in pth_holes}
    solder_regions: list[Polygon] = []
    metas: list[FixtureRegion] = []
    review_items: list[dict[str, Any]] = []
    used: set[str] = set()

    for i, cluster in enumerate(clusters):
        holes = [by_id[hid] for hid in cluster.hole_ids if hid in by_id]
        if not holes:
            continue
        used.update(h.id for h in holes)
        window = _opening_for_cluster(holes, cluster, params)
        window = _refine_with_mask(window, pcb, params)
        window = apply_directional_opening(window, params)
        confidence = cluster.confidence if cluster.component_type != "unknown" else min(cluster.confidence, 0.78)
        if len(holes) == 1:
            confidence = min(confidence, 0.70)
        rev_id = f"review-top-solder-{i+1}"
        rev_status = _status(review_actions, rev_id, confidence)
        polygons = list(window.geoms) if isinstance(window, MultiPolygon) else [window]
        source_id = cluster.refdes or cluster.id
        for poly in polygons:
            if poly.is_empty:
                continue
            if rev_status != "rejected":
                solder_regions.append(poly)
                metas.append(
                    FixtureRegion(
                        id=rev_id,
                        region_type="solder_opening",
                        geometry=poly,
                        source_type="semantic_component",
                        source_ids=(source_id,),
                        confidence=confidence,
                        parameters={
                            "thtKind": cluster.component_type,
                            "holeCount": len(holes),
                            "sourceType": "semantic_component",
                        },
                    )
                )
        if confidence < 0.85:
            review_items.append({
                "id": rev_id,
                "type": "top_solder_region",
                "status": rev_status,
                "title": f"TOP 插件上锡窗口 #{i+1} 确认",
                "description": f"语义识别 {cluster.component_type}（{len(holes)} pins），波峰焊透锡窗口已预留 {params['solderClearanceMm']}mm 间距。",
                "confidence": confidence,
                "geometryId": rev_id,
                "mandatory": False,
                "x": holes[0].x,
                "y": holes[0].y,
                "sourceType": "semantic_component",
                "sourceIds": [source_id],
            })

    leftovers = [h for h in pth_holes if h.id not in used]
    if leftovers:
        extra, extra_reviews, extra_meta = _greedy_fallback(pcb, leftovers, params, review_actions, start_index=len(clusters) + 1)
        extra, extra_meta = _merge_close(extra, extra_meta, params)
        solder_regions.extend(extra)
        review_items.extend(extra_reviews)
        metas.extend(extra_meta)
    return solder_regions, review_items, metas


def _opening_for_cluster(
    holes: list[DrillHit],
    cluster: ThroughHoleComponent,
    params: dict[str, Any],
) -> Polygon:
    clearance = params["solderClearanceMm"]
    min_outer = params.get("solderMinOuterDiameterMm", 3.0)

    if len(holes) == 1:
        h = holes[0]
        r = max(h.diameter_mm / 2 + clearance, min_outer / 2)
        return Point(h.x, h.y).buffer(r)

    kind = cluster.component_type
    if kind in {"1xn", "2xn", "dip"} or (cluster.inferred_rows in {1, 2} and len(holes) >= 2):
        return _oriented_capsule(holes, cluster, clearance, min_outer)

    pads = [Point(h.x, h.y).buffer(max(h.diameter_mm / 2 + clearance, min_outer / 2)) for h in holes]
    merged = unary_union(pads)
    if len(holes) >= 2:
        merged = merged.convex_hull.buffer(0.2, join_style="round")
    return merged


def _oriented_capsule(
    holes: list[DrillHit],
    cluster: ThroughHoleComponent,
    clearance: float,
    min_outer: float,
) -> Polygon:
    xs = [h.x for h in holes]
    ys = [h.y for h in holes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    r = max(max(h.diameter_mm for h in holes) / 2 + clearance, min_outer / 2)
    # Expand bbox by pad radius so a 1xN header becomes a rounded slot, not a huge hull.
    raw = box(min_x - r, min_y - r, max_x + r, max_y + r)
    # Round ends along the long axis.
    return raw.buffer(0.2, join_style="round")


def _refine_with_mask(window: Polygon, pcb: PCBGeometry, params: dict[str, Any]) -> Polygon:
    bot_mask = pcb.bottom_soldermask
    clearance = params["solderClearanceMm"]
    if bot_mask is None or bot_mask.is_empty or window.is_empty:
        return window
    try:
        intersecting_pads = bot_mask.intersection(window.buffer(1.0))
        if intersecting_pads.is_empty:
            return window
        expanded_pads = intersecting_pads.buffer(clearance, join_style="round")
        combined = unary_union([window, expanded_pads])
        return combined if not combined.is_empty else window
    except Exception:
        return window


def _merge_close(
    regions: list[Polygon],
    metas: list[FixtureRegion],
    params: dict[str, Any],
) -> tuple[list[Polygon], list[FixtureRegion]]:
    merge_d = float(params.get("solderOpeningMergeDistanceMm", 2.0))
    if len(regions) < 2 or merge_d <= 0:
        return regions, metas
    merged = list(regions)
    merged_metas = list(metas)
    changed = True
    while changed:
        changed = False
        nxt: list[Polygon] = []
        nxt_m: list[FixtureRegion] = []
        skip: set[int] = set()
        for i, a in enumerate(merged):
            if i in skip:
                continue
            acc = a
            acc_meta = merged_metas[i] if i < len(merged_metas) else None
            for j in range(i + 1, len(merged)):
                if j in skip:
                    continue
                b = merged[j]
                if acc.distance(b) < merge_d:
                    acc = unary_union([acc, b]).convex_hull.buffer(0.05, join_style="round")
                    skip.add(j)
                    changed = True
            nxt.append(acc)
            if acc_meta is not None:
                acc_meta.geometry = acc
                nxt_m.append(acc_meta)
        merged, merged_metas = nxt, nxt_m
    return merged, merged_metas


def _greedy_fallback(
    pcb: PCBGeometry,
    pth_holes: list[DrillHit],
    params: dict[str, Any],
    review_actions: dict[str, str] | None,
    start_index: int = 1,
) -> tuple[list[Polygon], list[dict[str, Any]], list[FixtureRegion]]:
    solder_regions: list[Polygon] = []
    review_items: list[dict[str, Any]] = []
    metas: list[FixtureRegion] = []
    clearance = params["solderClearanceMm"]
    min_outer_dia = params.get("solderMinOuterDiameterMm", 3.0)

    clusters: list[list[DrillHit]] = []
    for hole in pth_holes:
        placed = False
        for cluster in clusters:
            if any(math.hypot(hole.x - ch.x, hole.y - ch.y) <= 6.0 for ch in cluster):
                cluster.append(hole)
                placed = True
                break
        if not placed:
            clusters.append([hole])

    bot_mask = pcb.bottom_soldermask
    for i, cluster in enumerate(clusters):
        points = [Point(h.x, h.y).buffer(max(h.diameter_mm / 2 + clearance, min_outer_dia / 2)) for h in cluster]
        merged_window = unary_union(points)
        if len(cluster) >= 2:
            merged_window = merged_window.convex_hull.buffer(0.2, join_style="round")
        if bot_mask and not bot_mask.is_empty and not merged_window.is_empty:
            try:
                intersecting_pads = bot_mask.intersection(merged_window.buffer(1.0))
                if not intersecting_pads.is_empty:
                    expanded_pads = intersecting_pads.buffer(clearance, join_style="round")
                    combined = unary_union([merged_window, expanded_pads])
                    if not combined.is_empty:
                        merged_window = combined
            except Exception:
                pass
        merged_window = apply_directional_opening(merged_window, params)

        rev_id = f"review-top-solder-{start_index + i}"
        confidence = 0.88 if len(cluster) >= 2 else 0.70
        source = "gerber_fallback"
        rev_status = _status(review_actions, rev_id, confidence)
        if rev_status != "rejected":
            if isinstance(merged_window, MultiPolygon):
                geoms = [g for g in merged_window.geoms if not g.is_empty]
            elif not merged_window.is_empty:
                geoms = [merged_window]
            else:
                geoms = []
            for g in geoms:
                solder_regions.append(g)
                metas.append(
                    FixtureRegion(
                        id=rev_id,
                        region_type="solder_opening",
                        geometry=g,
                        source_type=source,
                        source_ids=tuple(h.id for h in cluster),
                        confidence=confidence,
                        parameters={"sourceType": source, "holeCount": len(cluster)},
                    )
                )
        if confidence < 0.85:
            review_items.append({
                "id": rev_id,
                "type": "top_solder_region",
                "status": rev_status,
                "title": f"TOP 插件上锡窗口 #{start_index + i} 确认",
                "description": f"检测到 {len(cluster)} 个 PTH 引脚组，波峰焊透锡窗口已预留 {clearance}mm 间距。",
                "confidence": confidence,
                "geometryId": rev_id,
                "mandatory": False,
                "x": cluster[0].x,
                "y": cluster[0].y,
                "sourceType": source,
            })
    return solder_regions, review_items, metas


def _status(review_actions: dict[str, str] | None, rev_id: str, confidence: float) -> str:
    default = "accepted" if confidence >= 0.85 else "pending"
    if review_actions:
        return review_actions.get(rev_id, default)
    return default


def wave_leading_trailing(direction: str) -> tuple[str, str]:
    """Leading is the edge that meets the wave first; trailing is the exit edge."""
    mapping = {
        "+X": ("-X", "+X"),
        "-X": ("+X", "-X"),
        "+Y": ("-Y", "+Y"),
        "-Y": ("+Y", "-Y"),
    }
    return mapping.get(str(direction), ("-X", "+X"))


def apply_directional_opening(window: Polygon, params: dict[str, Any]) -> Polygon:
    """Stretch / chamfer an opening along waveDirection. No-op unless enabled."""
    if window is None or window.is_empty:
        return window
    if not params.get("directionalOpeningEnabled"):
        return window
    direction = str(params.get("waveDirection", "+X"))
    if direction not in {"+X", "-X", "+Y", "-Y"}:
        return window
    lead = float(params.get("solderLeadingExtensionMm", 0.0) or 0.0)
    trail = float(params.get("solderTrailingExtensionMm", 0.0) or 0.0)
    side = float(params.get("solderSideClearanceMm", 0.0) or 0.0)
    entry_c = float(params.get("solderEntryChamferMm", 0.0) or 0.0)
    exit_c = float(params.get("solderExitChamferMm", 0.0) or 0.0)
    if lead <= 0 and trail <= 0 and side <= 0 and entry_c <= 0 and exit_c <= 0:
        return window

    extras = [window]
    axis_x = direction in {"+X", "-X"}
    leading_neg = direction in {"+X", "+Y"}
    if axis_x:
        extras.append(translate(window, xoff=-lead if leading_neg else lead))
        extras.append(translate(window, xoff=trail if leading_neg else -trail))
        if side > 0:
            extras.append(translate(window, yoff=side))
            extras.append(translate(window, yoff=-side))
    else:
        extras.append(translate(window, yoff=-lead if leading_neg else lead))
        extras.append(translate(window, yoff=trail if leading_neg else -trail))
        if side > 0:
            extras.append(translate(window, xoff=side))
            extras.append(translate(window, xoff=-side))

    expanded = unary_union(extras)
    if expanded.is_empty:
        return window
    expanded = _apply_end_chamfers(expanded, direction, entry_c, exit_c)
    if expanded.geom_type == "MultiPolygon":
        expanded = max(expanded.geoms, key=lambda g: g.area)
    return expanded if not expanded.is_empty else window


def _apply_end_chamfers(geom: Polygon, direction: str, entry: float, exit_c: float) -> Polygon:
    if entry <= 0 and exit_c <= 0:
        return geom
    minx, miny, maxx, maxy = geom.bounds
    cuts: list[Polygon] = []
    if direction == "+X":
        cuts.extend(_end_triangles(minx, miny, maxy, entry, inward=+1, vertical=False))
        cuts.extend(_end_triangles(maxx, miny, maxy, exit_c, inward=-1, vertical=False))
    elif direction == "-X":
        cuts.extend(_end_triangles(maxx, miny, maxy, entry, inward=-1, vertical=False))
        cuts.extend(_end_triangles(minx, miny, maxy, exit_c, inward=+1, vertical=False))
    elif direction == "+Y":
        cuts.extend(_end_triangles(miny, minx, maxx, entry, inward=+1, vertical=True))
        cuts.extend(_end_triangles(maxy, minx, maxx, exit_c, inward=-1, vertical=True))
    elif direction == "-Y":
        cuts.extend(_end_triangles(maxy, minx, maxx, entry, inward=-1, vertical=True))
        cuts.extend(_end_triangles(miny, minx, maxx, exit_c, inward=+1, vertical=True))
    if not cuts:
        return geom
    try:
        result = geom.difference(unary_union(cuts))
    except Exception:
        return geom
    return result if not result.is_empty else geom


def _end_triangles(edge: float, a0: float, a1: float, size: float, inward: int, vertical: bool) -> list[Polygon]:
    if size <= 0:
        return []
    tris: list[Polygon] = []
    for end in (a0, a1):
        sign = 1 if end == a0 else -1
        if vertical:
            # edge is Y, a is X
            tris.append(Polygon([
                (end, edge),
                (end + sign * size, edge),
                (end, edge + inward * size),
            ]))
        else:
            tris.append(Polygon([
                (edge, end),
                (edge + inward * size, end),
                (edge, end + sign * size),
            ]))
    return tris

