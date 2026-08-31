"""Locating pin optimizer. Farthest eligible pair remains the auto-select fallback."""
from __future__ import annotations

import math
from typing import Any

from shapely.geometry import Point

from app.models.geometry import PCBGeometry


def generate_locating_pins(
    pcb: PCBGeometry,
    params: dict[str, Any],
    manual_pins: list[str] | None = None,
    review_actions: dict[str, str] | None = None,
    keepouts: list | None = None,
    solder_regions: list | None = None,
    clamp_holes: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    holes = pcb.holes

    if not holes:
        review_items.append({
            "id": "review-locating-no-drills",
            "type": "CONFIRM_NO_NPTH_AVAILABLE",
            "status": "pending",
            "title": "未检测到定位孔 - 请确认固定方案",
            "description": "Excellon 钻孔中无可用定位孔。请确认本板无可用 NPTH 定位孔，或手动指定定位孔位置。",
            "confidence": 0.0,
            "mandatory": True,
        })
        return [], [], review_items

    min_x, min_y, max_x, max_y = pcb.outline.bounds
    preferred_npth = bool(params.get("preferredNPTH", True))
    min_dia = float(params.get("minPinHoleDiameterMm", 2.0))
    max_dia = float(params.get("maxPinHoleDiameterMm", 4.5))
    pref_min = float(params.get("preferredPinDiameterMinMm", 2.5))
    pref_max = float(params.get("preferredPinDiameterMaxMm", 4.5))
    edge_bonus = float(params.get("pinEdgeBonusMm", 15.0))
    pin_off = float(params.get("pinDiameterOffsetMm", 0.1))
    pin_min = float(params.get("pinDiameterMinMm", 1.5))
    pin_max = float(params.get("pinDiameterMaxMm", 4.0))

    for hole in holes:
        score = 0.0
        reasons: list[str] = []
        rejection: list[str] = []
        is_slot = getattr(hole, "kind", "hole") == "slot"

        if is_slot:
            score -= 10.0
            rejection.append("腰圆槽/长条孔无法作为定位销孔")

        if not is_slot and pref_min <= hole.diameter_mm <= pref_max:
            score += 4.0
            reasons.append("孔径适中适合打定位销 (2.5~4.5mm)")
        elif not is_slot and min_dia <= hole.diameter_mm < pref_min:
            score += 2.0
            reasons.append("孔径偏小但仍可作为候选")
        elif not is_slot and hole.diameter_mm > max(max_dia, 5.0):
            score -= 3.0
            rejection.append("孔径过大可能为螺丝固定孔")

        if hole.plated is False and not is_slot:
            if preferred_npth:
                score += 4.0
            reasons.append("非金属化孔 (NPTH)")
        elif hole.plated is True:
            score -= 1.0
            reasons.append("金属化孔 (PTH) 降权")

        dist_to_edge = min(hole.x - min_x, max_x - hole.x, hole.y - min_y, max_y - hole.y)
        if dist_to_edge <= edge_bonus and not is_slot:
            score += 3.0
            reasons.append("靠近边缘工艺边区域")

        conflict_notes = _conflict_penalties(hole, keepouts, solder_regions, clamp_holes)
        for note, penalty in conflict_notes:
            score += penalty
            if penalty < 0:
                rejection.append(note)
            else:
                reasons.append(note)

        if is_slot:
            eligible = False
        elif hole.diameter_mm + 1e-9 < min_dia:
            rejection.append(f"孔径小于 {min_dia:.1f}mm")
            eligible = False
        else:
            eligible = score >= 4.0 or (hole.plated is False and hole.diameter_mm >= min_dia)
        # Keep historical rejectionReasons payload (includes positive reasons)
        # plus a dedicated reasons list.
        combined_legacy = rejection + [r for r in reasons if r not in rejection]

        cand = {
            "id": f"pin-cand-{hole.id}",
            "drillId": hole.id,
            "x": hole.x,
            "y": hole.y,
            "diameterMm": hole.diameter_mm,
            "plated": hole.plated,
            "score": round(score, 1),
            "eligible": eligible,
            "selected": False,
            "pinDiameterMm": min(max(hole.diameter_mm - pin_off, pin_min), pin_max),
            "rejectionReasons": combined_legacy,
            "reasons": reasons,
            "rejectionReasonsOnly": rejection,
        }
        candidates.append(cand)

    eligible_cands = [c for c in candidates if c["eligible"]]
    selected_pins: list[dict[str, Any]] = []

    if manual_pins:
        manual_set = set(manual_pins)
        for c in candidates:
            if c["drillId"] in manual_set or c["id"] in manual_set or f"pin-{c['drillId']}" in manual_set:
                c["selected"] = True
                selected_pins.append({"id": f"pin-{c['drillId']}", "x": c["x"], "y": c["y"], "diameter": c["pinDiameterMm"]})
    else:
        pair = _farthest_pair(eligible_cands)
        if pair:
            for c in pair:
                c["selected"] = True
                selected_pins.append({"id": f"pin-{c['drillId']}", "x": c["x"], "y": c["y"], "diameter": c["pinDiameterMm"]})
        elif len(eligible_cands) == 1:
            eligible_cands[0]["selected"] = True
            c = eligible_cands[0]
            selected_pins.append({"id": f"pin-{c['drillId']}", "x": c["x"], "y": c["y"], "diameter": c["pinDiameterMm"]})

    if len(selected_pins) < 2:
        review_status = "pending"
        if review_actions and review_actions.get("review-locating-pins"):
            review_status = review_actions["review-locating-pins"]
        review_items.append({
            "id": "review-locating-pins",
            "type": "locating_pin_candidate",
            "status": review_status,
            "title": "定位销数量或置信度待确认",
            "description": f"已识别 {len(selected_pins)} 个高置信度定位孔，请在 CAD 视图中确认定位孔选择。",
            "confidence": 0.65 if selected_pins else 0.3,
            "mandatory": True,
            "data": {"candidates": [c["id"] for c in candidates[:6]]},
        })

    return candidates, selected_pins, review_items


def _conflict_penalties(hole, keepouts, solder_regions, clamp_holes) -> list[tuple[str, float]]:
    notes: list[tuple[str, float]] = []
    pt = Point(hole.x, hole.y)
    if keepouts:
        for k in keepouts:
            if k is not None and not getattr(k, "is_empty", False) and k.contains(pt):
                notes.append(("与 BOT 避位区冲突", -8.0))
                break
    if solder_regions:
        for s in solder_regions:
            if s is not None and not getattr(s, "is_empty", False) and s.contains(pt):
                notes.append(("与上锡窗口冲突", -8.0))
                break
    if clamp_holes:
        for clamp in clamp_holes:
            dist = math.hypot(hole.x - clamp["x"], hole.y - clamp["y"])
            if dist < 10.0:
                notes.append(("与压扣过近", -3.0))
                break
    return notes


def _farthest_pair(eligible: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Historical auto-select: the eligible pair with maximum Euclidean distance.

    Span (min(dx, dy)) is used only as a tie-breaker so XY coverage is preferred
    when two pairs share the same distance.
    """
    if len(eligible) < 2:
        return None
    best_pair = None
    max_dist = -1.0
    best_span = -1.0
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            c1, c2 = eligible[i], eligible[j]
            dx = abs(c1["x"] - c2["x"])
            dy = abs(c1["y"] - c2["y"])
            dist = math.hypot(dx, dy)
            span = min(dx, dy)
            if dist > max_dist or (abs(dist - max_dist) < 1e-9 and span > best_span):
                max_dist = dist
                best_span = span
                best_pair = (c1, c2)
    return best_pair
