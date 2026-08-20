"""Deterministic fixture geometry generator with upgraded Keepout, Solder, Pin, Relief and Mounting holes."""
from __future__ import annotations

import hashlib
import math
from typing import Any

from shapely import normalize, to_wkb, make_valid
from shapely.geometry import Point, Polygon, MultiPolygon, box
from shapely.ops import unary_union

from app.models.geometry import FixtureGeometry, PCBGeometry, DrillHit
from app.services.fixture.drc import run_drc


class FixtureGenerationError(ValueError):
    pass


class FixtureGenerator:
    def __init__(self, pcb_analysis: dict[str, Any]):
        self.pcb: PCBGeometry | None = pcb_analysis.get("pcb_geometry")
        if self.pcb is None or self.pcb.outline is None or self.pcb.outline.is_empty:
            raise FixtureGenerationError("缺少真实 PCBGeometry，禁止使用估算外形生成治具。")

    def generate(self, parameters: dict[str, Any], review_actions: dict[str, str] | None = None, manual_pins: list[str] | None = None, custom_regions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        params = self._parameters(parameters)
        
        # 1. 沉板区生成 + R1.85 铣刀角清角 (Corner Relief)
        sink_region = self._generate_sink_region_with_relief(self.pcb.outline, params)
        if sink_region.is_empty or not sink_region.is_valid:
            raise FixtureGenerationError("PCB 外形偏移后无法形成有效沉板区。")

        # 2. 治具主体外框
        body = self._fixture_body(sink_region, params)
        
        # 3. 辅件与安装位
        handholds = self._handholds(sink_region, params)
        clamp_holes = self._clamp_holes(sink_region, params)
        rails, barriers, barrier_mount_holes = self._rails_and_barriers(body, params)
        
        # 4. 定位销与候选
        locating_candidates, locating_pins, locating_review = self._locating_pin_candidates(params, manual_pins, review_actions)
        
        # 5. BOT 避位区
        keepouts, keepout_review = self._bottom_keepouts(params, review_actions)
        
        # 6. TOP 上锡窗口
        solder_regions, solder_review = self._solder_regions(params, review_actions)
        
        # 7. TOP 丝印弹簧卡安装孔
        spring_clips, spring_clip_review = self._front_panel_spring_clips(params, review_actions)
        
        # 7.5. 自定义开窗/避位区注入 (AI / 工程师非标建设)
        if custom_regions:
            for cr in custom_regions:
                cx = float(cr.get("x", 0.0))
                cy = float(cr.get("y", 0.0))
                w = float(cr.get("width", 10.0))
                h = float(cr.get("height", 10.0))
                rtype = cr.get("regionType", "keepout")
                poly = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                if not poly.is_empty:
                    if rtype == "keepout":
                        keepouts.append(poly)
                    elif rtype == "solder":
                        solder_regions.append(poly)

        # 汇总 Review 项
        review_items = [*locating_review, *keepout_review, *solder_review, *spring_clip_review]
        pending_mandatory_reviews = [r for r in review_items if r.get("mandatory", True) and r.get("status") == "pending"]

        provisional = FixtureGeometry(
            pcb=self.pcb,
            body=body,
            sink_region=sink_region,
            keepout_regions=keepouts,
            solder_regions=solder_regions,
            locating_pins=locating_pins,
            locating_pin_candidates=locating_candidates,
            clamp_holes=clamp_holes,
            handholds=handholds,
            rails=rails,
            solder_barriers=barriers,
            solder_barrier_mount_holes=barrier_mount_holes,
            spring_clip_holes=spring_clips,
            drc_issues=[],
            review_items=review_items,
            parameters=params,
            geometry_sha256="",
        )
        provisional.drc_issues = run_drc(provisional)
        provisional.geometry_sha256 = self._geometry_digest(provisional)

        status = "review_required" if len(pending_mandatory_reviews) > 0 else "completed"

        return {
            "fixture_geometry": provisional,
            "pcb_outline": self.pcb.outline,
            "fixture_outline": body,
            "sink_area": sink_region,
            "keepout_zones": keepouts,
            "solder_windows": solder_regions,
            "pins": locating_pins,
            "locating_candidates": locating_candidates,
            "clips": clamp_holes,
            "handholds": handholds,
            "rails": rails,
            "solder_barriers": barriers,
            "solder_barrier_mount_holes": barrier_mount_holes,
            "spring_clips": spring_clips,
            "issues": provisional.drc_issues,
            "reviewItems": review_items,
            "status": status,
            "fixtureWidth": provisional.width,
            "fixtureHeight": provisional.height,
            "geometrySha256": provisional.geometry_sha256,
            "featureSummary": {
                "sinkRegionCount": 1,
                "keepoutRegionCount": len(keepouts),
                "solderWindowCount": len(solder_regions),
                "locatingPinCount": len(locating_pins),
                "locatingCandidateCount": len(locating_candidates),
                "clampCount": len(clamp_holes),
                "barrierMountHoleCount": len(barrier_mount_holes),
                "springClipCount": len(spring_clips),
            },
        }

    def _parameters(self, supplied: dict[str, Any]) -> dict[str, float]:
        defaults = {
            "sinkClearanceMm": 0.2,
            "keepoutClearanceMm": 0.7,
            "solderClearanceMm": 3.0,
            "filletRadiusMm": 1.85,
            "clampHoleDiameterMm": 3.4,
            "clampOffsetMm": 10.0,
            "handholdWidthMm": 20.0,
            "handholdHeightMm": 40.0,
            "handholdOverlapMm": 1.0,
            "handholdCornerRadiusMm": 2.0,
            "fixtureMarginXmm": 20.0,
            "fixtureMarginYmm": 30.0,
            "fixtureCornerRadiusMm": 5.0,
            "railWidthMm": 5.0,
            "solderBarrierWidthMm": 10.0,
            "springClipRadiusMm": 2.45,
            "keepoutInnerFilletMm": 1.5,
            "solderMinOuterDiameterMm": 3.0,
            "minimumMaterialWebMm": 2.0,
            "fixtureSizeRoundStepMm": 5.0,
        }
        merged: dict[str, float] = {}
        for key, default in defaults.items():
            value = supplied.get(key, default) if supplied else default
            try:
                merged[key] = float(value)
            except (TypeError, ValueError):
                merged[key] = default
        return merged

    def _generate_sink_region_with_relief(self, outline: Polygon, params: dict[str, float]) -> Polygon:
        """PCB 外扩 0.2mm，并在外凸角做 R1.85 铣刀清角切削"""
        sink_base = outline.buffer(params["sinkClearanceMm"], join_style="round")
        radius = params["filletRadiusMm"]
        
        # 寻找凸角顶点加清角圆孔
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

    def _fixture_body(self, sink_region: Polygon, params: dict[str, float]) -> Polygon:
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

    def _handholds(self, sink_region: Polygon, params: dict[str, float]) -> list[Polygon]:
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

    def _clamp_holes(self, sink_region: Polygon, params: dict[str, float]) -> list[dict[str, Any]]:
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

    def _rails_and_barriers(self, body: Polygon, params: dict[str, float]) -> tuple[list[Polygon], list[Polygon], list[dict[str, Any]]]:
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

        if barrier_height_span > 20:
            y_steps = [barrier_y_start, barrier_y_start + barrier_height_span / 2, barrier_y_end]
        else:
            y_steps = [(min_y + max_y) / 2]

        for i, y in enumerate(y_steps):
            mount_holes.append({
                "id": f"barrier-mount-left-{i+1}",
                "x": round(min_x + barrier_w / 2, 3),
                "y": round(y, 3),
                "diameter": 3.2,
            })
            mount_holes.append({
                "id": f"barrier-mount-right-{i+1}",
                "x": round(max_x - barrier_w / 2, 3),
                "y": round(y, 3),
                "diameter": 3.2,
            })

        return [top_rail, bot_rail], [left_barrier, right_barrier], mount_holes

    def _locating_pin_candidates(
        self,
        params: dict[str, float],
        manual_pins: list[str] | None = None,
        review_actions: dict[str, str] | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        candidates: list[dict[str, Any]] = []
        review_items: list[dict[str, Any]] = []
        holes = self.pcb.holes

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

        min_x, min_y, max_x, max_y = self.pcb.outline.bounds
        for hole in holes:
            score = 0.0
            reasons = []
            
            # 孔径适中 (2.5mm ~ 4.5mm 最佳)
            if 2.5 <= hole.diameter_mm <= 4.5:
                score += 4.0
                reasons.append("孔径适中适合打定位销 (2.5~4.5mm)")
            elif 1.8 <= hole.diameter_mm < 2.5:
                score += 2.0
            elif hole.diameter_mm > 5.0:
                score -= 3.0
                reasons.append("孔径过大可能为螺丝固定孔")

            # NPTH 非金属化孔优先
            if hole.plated is False:
                score += 4.0
                reasons.append("非金属化孔 (NPTH)")
            elif hole.plated is True:
                score -= 1.0

            # 靠近板边角落
            dist_to_edge = min(hole.x - min_x, max_x - hole.x, hole.y - min_y, max_y - hole.y)
            if dist_to_edge <= 15.0:
                score += 3.0
                reasons.append("靠近边缘工艺边区域")

            eligible = score >= 4.0 or (hole.plated is False and hole.diameter_mm >= 2.0)
            
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
                "pinDiameterMm": min(max(hole.diameter_mm - 0.1, 1.5), 4.0),
                "rejectionReasons": reasons,
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
            # 自动寻找对角距离最大的 2 个孔
            if len(eligible_cands) >= 2:
                best_pair = None
                max_dist = -1.0
                for i in range(len(eligible_cands)):
                    for j in range(i + 1, len(eligible_cands)):
                        c1, c2 = eligible_cands[i], eligible_cands[j]
                        d = math.hypot(c1["x"] - c2["x"], c1["y"] - c2["y"])
                        if d > max_dist:
                            max_dist = d
                            best_pair = (c1, c2)
                if best_pair:
                    for c in best_pair:
                        c["selected"] = True
                        selected_pins.append({"id": f"pin-{c['drillId']}", "x": c["x"], "y": c["y"], "diameter": c["pinDiameterMm"]})
            elif len(eligible_cands) == 1:
                eligible_cands[0]["selected"] = True
                selected_pins.append({"id": f"pin-{eligible_cands[0]['drillId']}", "x": eligible_cands[0]["x"], "y": eligible_cands[0]["y"], "diameter": eligible_cands[0]["pinDiameterMm"]})

        # 置信度判断：若定位销少于 2 个或总分偏低，生成 Review
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

    def _bottom_keepouts(self, params: dict[str, float], review_actions: dict[str, str] | None = None) -> tuple[list[Polygon], list[dict[str, Any]]]:
        """BOT 元件/丝印/阻焊开窗空间聚类与避位生成"""
        keepouts: list[Polygon] = []
        review_items: list[dict[str, Any]] = []
        bot_silk = self.pcb.bottom_silkscreen
        bot_mask = self.pcb.bottom_soldermask
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
            return [], review_items

        combined = unary_union(geom_candidates)
        buffered = combined.buffer(clearance, join_style="round")
        fillet_r = params.get("keepoutInnerFilletMm", 1.5)
        if fillet_r > 0:
            filleted = buffered.buffer(-fillet_r).buffer(fillet_r)
            if not filleted.is_empty:
                buffered = filleted
        polygons = list(buffered.geoms) if isinstance(buffered, MultiPolygon) else [buffered]

        for i, poly in enumerate(polygons):
            if poly.is_empty or poly.area < 1.0:
                continue
            
            confidence = 0.90 if poly.area > 5.0 else 0.75
            rev_id = f"review-bot-keepout-{i+1}"
            rev_status = review_actions.get(rev_id, "accepted" if confidence >= 0.85 else "pending") if review_actions else ("accepted" if confidence >= 0.85 else "pending")
            
            if rev_status != "rejected":
                keepouts.append(poly)

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
                })

        return keepouts, review_items

    def _solder_regions(self, params: dict[str, float], review_actions: dict[str, str] | None = None) -> tuple[list[Polygon], list[dict[str, Any]]]:
        """TOP 插件焊盘/PTH 钻孔聚类与上锡窗口生成"""
        solder_regions: list[Polygon] = []
        review_items: list[dict[str, Any]] = []
        holes = self.pcb.holes
        pth_holes = [h for h in holes if h.plated is True or (h.plated is None and h.diameter_mm < 2.0)]
        clearance = params["solderClearanceMm"]

        if not pth_holes:
            review_items.append({
                "id": "review-top-solder-no-pth",
                "type": "CONFIRM_NO_TOP_THT",
                "status": review_actions.get("review-top-solder-no-pth", "pending") if review_actions else "pending",
                "title": "未检测到 PTH 通孔 - 请确认无需上锡窗口",
                "description": "未检测到明确的 PTH 通孔引脚。若本板确实无插件焊接需求，请确认放行；否则请重新指定钻孔文件。",
                "confidence": 0.5,
                "mandatory": True,
            })
            return [], review_items

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

        bot_mask = self.pcb.bottom_soldermask
        min_outer_dia = params.get("solderMinOuterDiameterMm", 3.0)

        for i, cluster in enumerate(clusters):
            points = [Point(h.x, h.y).buffer(max(h.diameter_mm / 2 + clearance, min_outer_dia / 2)) for h in cluster]
            merged_window = unary_union(points)

            # 结合底部阻焊开窗 (GBS) 取包络与多边形槽孔 (一字型/方框型)
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

            rev_id = f"review-top-solder-{i+1}"
            confidence = 0.88 if len(cluster) >= 2 else 0.70
            rev_status = review_actions.get(rev_id, "accepted" if confidence >= 0.85 else "pending") if review_actions else ("accepted" if confidence >= 0.85 else "pending")

            if rev_status != "rejected":
                if isinstance(merged_window, MultiPolygon):
                    for sub_w in merged_window.geoms:
                        if not sub_w.is_empty:
                            solder_regions.append(sub_w)
                elif not merged_window.is_empty:
                    solder_regions.append(merged_window)

            if confidence < 0.85:
                review_items.append({
                    "id": rev_id,
                    "type": "top_solder_region",
                    "status": rev_status,
                    "title": f"TOP 插件上锡窗口 #{i+1} 确认",
                    "description": f"检测到 {len(cluster)} 个 PTH 引脚组，波峰焊透锡窗口已预留 {clearance}mm 间距。",
                    "confidence": confidence,
                    "geometryId": rev_id,
                    "mandatory": False,
                    "x": cluster[0].x,
                    "y": cluster[0].y,
                })

        return solder_regions, review_items


    def _front_panel_spring_clips(self, params: dict[str, float], review_actions: dict[str, str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """TOP 丝印层 (GTO) 元器件中心点 -> 前挡板弹簧卡安装孔 R2.45mm"""
        clips: list[dict[str, Any]] = []
        review_items: list[dict[str, Any]] = []
        top_silk = self.pcb.top_silkscreen
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

        from shapely.geometry import GeometryCollection, LineString, MultiLineString
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
        else:
            polygons = []

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
            if not self.pcb.outline.contains(Point(cx, cy)):
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
    def _geometry_digest(self, fixture: FixtureGeometry) -> str:
        h = hashlib.sha256()
        h.update(to_wkb(normalize(make_valid(fixture.body)), hex=False))
        h.update(to_wkb(normalize(make_valid(fixture.sink_region)), hex=False))
        sorted_pins = sorted(fixture.locating_pins, key=lambda p: (p['x'], p['y']))
        for pin in sorted_pins:
            h.update(f"{pin['x']}:{pin['y']}:{pin['diameter']}".encode("utf-8"))
        sorted_clamps = sorted(fixture.clamp_holes, key=lambda c: (c['x'], c['y']))
        for clip in sorted_clamps:
            h.update(f"{clip['x']}:{clip['y']}:{clip['diameter']}".encode("utf-8"))
        sorted_springs = sorted(getattr(fixture, "spring_clip_holes", []), key=lambda s: (s['x'], s['y']))
        for sp in sorted_springs:
            h.update(f"{sp['x']}:{sp['y']}:{sp['diameter']}".encode("utf-8"))
        sorted_keepouts = sorted([kz for kz in fixture.keepout_regions if not kz.is_empty], key=lambda k: (k.centroid.x, k.centroid.y))
        for kz in sorted_keepouts:
            h.update(to_wkb(normalize(make_valid(kz)), hex=False))
        sorted_solders = sorted([sw for sw in fixture.solder_regions if not sw.is_empty], key=lambda s: (s.centroid.x, s.centroid.y))
        for sw in sorted_solders:
            h.update(to_wkb(normalize(make_valid(sw)), hex=False))
        return h.hexdigest()





